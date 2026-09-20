import asyncio
import json
import queue
import socket
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

REPORTS_DIR = Path.home() / ".tunnelit" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

SLOW_THRESHOLD_MS = 2000
ASSET_EXTENSIONS = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".svg", ".map"}


def path_has_asset_extension(path: str) -> bool:
    return any(path.lower().endswith(ext) for ext in ASSET_EXTENSIONS)


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return s.getsockname()[1]


class RequestMetric(BaseModel):
    request_id: str
    method: str
    path: str
    query: str
    status_code: int
    duration_ms: float
    request_bytes: int
    response_bytes: int
    timestamp: datetime = Field(default_factory=datetime.now)
    is_error: bool = False
    is_slow: bool = False
    is_asset_404: bool = False


class SummaryStats(BaseModel):
    total_requests: int = 0
    by_status: Dict[str, int] = Field(default_factory=dict)
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    slow_count: int = 0
    error_count: int = 0
    total_request_bytes: int = 0
    total_response_bytes: int = 0
    top_paths: List[Tuple[str, int]] = Field(default_factory=list)
    top_errors: List[Tuple[str, int]] = Field(default_factory=list)

    def update(self, metric: RequestMetric):
        self.total_requests += 1

        status_group = f"{metric.status_code // 100}xx"
        self.by_status[status_group] = self.by_status.get(status_group, 0) + 1

        self.total_request_bytes += metric.request_bytes
        self.total_response_bytes += metric.response_bytes

        if metric.is_slow:
            self.slow_count += 1
        if metric.is_error:
            self.error_count += 1

        self.avg_duration_ms = (
            (self.avg_duration_ms * (self.total_requests - 1) + metric.duration_ms)
            / self.total_requests
        )

        path_counts: Dict[str, int] = dict(self.top_paths)
        path_counts[metric.path] = path_counts.get(metric.path, 0) + 1
        self.top_paths = sorted(path_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        if metric.is_error:
            error_counts: Dict[str, int] = dict(self.top_errors)
            error_counts[metric.path] = error_counts.get(metric.path, 0) + 1
            self.top_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    def finalize(self, all_metrics: List[RequestMetric]):
        if all_metrics:
            durations = sorted(m.duration_ms for m in all_metrics)
            idx = int(len(durations) * 0.95)
            self.p95_duration_ms = durations[idx] if durations else 0.0


class SessionReport(BaseModel):
    tunnel_id: str
    public_url: str
    local_port: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    metrics: List[RequestMetric] = Field(default_factory=list)
    summary: SummaryStats = Field(default_factory=SummaryStats)

    def add_metric(self, metric: RequestMetric):
        self.metrics.append(metric)
        self.summary.update(metric)

    def finalize(self):
        self.ended_at = datetime.now()
        self.summary.finalize(self.metrics)

    def save(self) -> Path:
        self.finalize()
        timestamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        path = REPORTS_DIR / f"{self.tunnel_id}_{timestamp}.json"
        path.write_text(self.model_dump_json(indent=2))
        return path


class MetricsCollector:
    def __init__(self, tunnel_id: str, public_url: str, local_port: int):
        self.tunnel_id = tunnel_id
        self.public_url = public_url
        self.local_port = local_port
        self._queue: asyncio.Queue = asyncio.Queue()
        self._subscribers: List[queue.Queue] = []
        self._subscribers_lock = threading.Lock()
        self._report = SessionReport(
            tunnel_id=tunnel_id,
            public_url=public_url,
            local_port=local_port,
            started_at=datetime.now(),
        )
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._consume_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def add(self, metric: RequestMetric):
        try:
            self._queue.put_nowait(metric)
        except asyncio.QueueFull:
            pass

    def subscribe(self) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=100)
        with self._subscribers_lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._subscribers_lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def _bridge_to_subscribers(self, metric: RequestMetric):
        data = metric.model_dump_json()
        with self._subscribers_lock:
            for q in self._subscribers:
                try:
                    q.put_nowait(data)
                except queue.Full:
                    pass

    async def _consume_loop(self):
        while self._running:
            try:
                metric = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            self._report.add_metric(metric)
            self._bridge_to_subscribers(metric)

    def get_current_report(self) -> SessionReport:
        return self._report

    def finalize(self) -> Path:
        return self._report.save()

    @staticmethod
    def list_reports() -> List[Dict]:
        reports = []
        for path in sorted(REPORTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text())
                reports.append({
                    "id": path.stem,
                    "path": str(path),
                    "tunnel_id": data.get("tunnel_id"),
                    "public_url": data.get("public_url"),
                    "local_port": data.get("local_port"),
                    "started_at": data.get("started_at"),
                    "ended_at": data.get("ended_at"),
                    "total_requests": data.get("summary", {}).get("total_requests", 0),
                    "error_count": data.get("summary", {}).get("error_count", 0),
                })
            except Exception:
                continue
        return reports

    @staticmethod
    def load_report(report_id: str) -> Optional[SessionReport]:
        for path in REPORTS_DIR.glob("*.json"):
            if path.stem == report_id:
                try:
                    data = json.loads(path.read_text())
                    return SessionReport(**data)
                except Exception:
                    return None
        return None
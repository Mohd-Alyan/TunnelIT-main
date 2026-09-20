import base64
import time
import httpx
from .protocol import RequestMessage, ResponseMessage
from .config import settings
from .logging_config import logger
from .metrics import RequestMetric, SLOW_THRESHOLD_MS, path_has_asset_extension

HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"
}

class HTTPForwarder:
    def __init__(self, target_port: int, metrics_collector=None):
        self.target_port = target_port
        self.client = httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT)
        self.metrics_collector = metrics_collector

    async def close(self):
        await self.client.aclose()

    async def forward(self, req_msg: RequestMessage) -> ResponseMessage:
        start_time = time.monotonic()
        url = f"http://127.0.0.1:{self.target_port}{req_msg.path}"
        if req_msg.query:
            url = f"{url}?{req_msg.query}"
            
        headers = {}
        for k, v in req_msg.headers.items():
            if k.lower() not in HOP_BY_HOP_HEADERS and k.lower() != "host":
                headers[k] = v
        
        body_bytes = b""
        if req_msg.body:
            try:
                body_bytes = base64.b64decode(req_msg.body)
            except Exception as e:
                logger.error(f"Failed to decode request body for {req_msg.request_id}: {e}")
                error_resp = ResponseMessage(
                    request_id=req_msg.request_id,
                    status=400,
                    headers={},
                    body=base64.b64encode(b"Bad Request: invalid base64 body").decode('utf-8')
                )
                self._record_metric(req_msg, error_resp, body_bytes, start_time)
                return error_resp

        try:
            response = await self.client.request(
                method=req_msg.method,
                url=url,
                headers=headers,
                content=body_bytes
            )
            
            resp_headers = {}
            for k, v in response.headers.items():
                if k.lower() not in HOP_BY_HOP_HEADERS:
                    resp_headers[k] = v
                    
            resp_body_b64 = base64.b64encode(response.content).decode('utf-8')
            
            resp_msg = ResponseMessage(
                request_id=req_msg.request_id,
                status=response.status_code,
                headers=resp_headers,
                body=resp_body_b64
            )
            self._record_metric(req_msg, resp_msg, body_bytes, start_time)
            return resp_msg
        except httpx.RequestError as e:
            logger.error(f"Error forwarding request {req_msg.request_id} to local service: {e}")
            error_resp = ResponseMessage(
                request_id=req_msg.request_id,
                status=502,
                headers={},
                body=base64.b64encode(b"Bad Gateway: local service unavailable").decode('utf-8')
            )
            self._record_metric(req_msg, error_resp, body_bytes, start_time)
            return error_resp

    def _record_metric(self, req_msg: RequestMessage, resp_msg: ResponseMessage, request_bytes: bytes, start_time: float):
        if not self.metrics_collector:
            return
        duration_ms = (time.monotonic() - start_time) * 1000
        response_bytes = 0
        if resp_msg.body:
            try:
                response_bytes = len(base64.b64decode(resp_msg.body))
            except Exception:
                response_bytes = len(resp_msg.body)
        
        metric = RequestMetric(
            request_id=req_msg.request_id,
            method=req_msg.method,
            path=req_msg.path,
            query=req_msg.query,
            status_code=resp_msg.status,
            duration_ms=duration_ms,
            request_bytes=len(request_bytes),
            response_bytes=response_bytes,
            is_error=400 <= resp_msg.status < 600,
            is_slow=duration_ms > SLOW_THRESHOLD_MS,
            is_asset_404=resp_msg.status == 404 and path_has_asset_extension(req_msg.path),
        )
        self.metrics_collector.add(metric)
import typer
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from pathlib import Path
from typing import Optional
from .metrics import MetricsCollector, SessionReport

app = typer.Typer(name="report", help="Manage tunnel session reports")
console = Console()

@app.command("list")
def list_reports():
    """List all saved session reports"""
    reports = MetricsCollector.list_reports()
    
    if not reports:
        console.print("[yellow]No reports found[/yellow]")
        return
    
    table = Table(title="Tunnel It Session Reports")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Tunnel ID", style="yellow")
    table.add_column("Date", style="green")
    table.add_column("Duration", style="blue")
    table.add_column("Requests", justify="right", style="white")
    table.add_column("Errors", justify="right", style="red")
    
    for r in reports:
        started = r.get("started_at", "")
        ended = r.get("ended_at", "")
        duration = ""
        if started and ended:
            try:
                from datetime import datetime
                s = datetime.fromisoformat(started.replace('Z', '+00:00'))
                e = datetime.fromisoformat(ended.replace('Z', '+00:00'))
                duration = str(e - s).split('.')[0]
            except Exception:
                pass
        
        table.add_row(
            r["id"][:30],
            r["tunnel_id"] or "unknown",
            started[:19].replace('T', ' ') if started else "unknown",
            duration,
            str(r["total_requests"]),
            str(r["error_count"])
        )
    
    console.print(table)

@app.command("show")
def show_report(
    report_id: str = typer.Argument(..., help="Report ID to show"),
    format: str = typer.Option("json", "--format", "-f", help="Output format: json, html, md")
):
    """Show a specific report"""
    report = MetricsCollector.load_report(report_id)
    
    if not report:
        console.print(f"[red]Report '{report_id}' not found[/red]")
        raise typer.Exit(1)
    
    if format == "json":
        json_str = report.model_dump_json(indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        console.print(syntax)
    elif format == "md":
        md = generate_markdown_report(report)
        console.print(Markdown(md))
    elif format == "html":
        html = generate_html_report(report)
        console.print(html)
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)

@app.command("export")
def export_report(
    report_id: str = typer.Argument(..., help="Report ID to export"),
    output: Path = typer.Option(..., "--output", "-o", help="Output file path"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, html, md")
):
    """Export a report to a file"""
    report = MetricsCollector.load_report(report_id)
    
    if not report:
        console.print(f"[red]Report '{report_id}' not found[/red]")
        raise typer.Exit(1)
    
    if format == "json":
        content = report.model_dump_json(indent=2)
    elif format == "html":
        content = generate_html_report(report)
    elif format == "md":
        content = generate_markdown_report(report)
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(1)
    
    output.write_text(content)
    console.print(f"[green]Report exported to {output}[/green]")

def generate_markdown_report(report: SessionReport) -> str:
    lines = [
        f"# Tunnel It Session Report",
        f"",
        f"**Tunnel ID:** {report.tunnel_id}",
        f"**Public URL:** {report.public_url}",
        f"**Local Port:** {report.local_port}",
        f"**Started:** {report.started_at}",
        f"**Ended:** {report.ended_at or 'N/A'}",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Requests | {report.summary.total_requests} |",
        f"| 2xx Responses | {report.summary.by_status.get('2xx', 0)} |",
        f"| 3xx Responses | {report.summary.by_status.get('3xx', 0)} |",
        f"| 4xx Responses | {report.summary.by_status.get('4xx', 0)} |",
        f"| 5xx Responses | {report.summary.by_status.get('5xx', 0)} |",
        f"| Avg Latency | {report.summary.avg_duration_ms:.1f} ms |",
        f"| P95 Latency | {report.summary.p95_duration_ms:.1f} ms |",
        f"| Slow Requests (>2s) | {report.summary.slow_count} |",
        f"| Error Count | {report.summary.error_count} |",
        f"| Total Request Bytes | {report.summary.total_request_bytes:,} |",
        f"| Total Response Bytes | {report.summary.total_response_bytes:,} |",
        f"",
        f"## Top Paths",
        f"",
        f"| Path | Count |",
        f"|------|-------|",
    ]
    
    for path, count in report.summary.top_paths:
        lines.append(f"| {path} | {count} |")
    
    lines.extend([
        f"",
        f"## Top Errors",
        f"",
        f"| Path | Count |",
        f"|------|-------|",
    ])
    
    for path, count in report.summary.top_errors:
        lines.append(f"| {path} | {count} |")
    
    lines.extend([
        f"",
        f"## All Requests",
        f"",
        f"| Time | Method | Path | Status | Duration |",
        f"|------|--------|------|--------|----------|",
    ])
    
    for m in report.metrics:
        time_str = m.timestamp.strftime("%H:%M:%S")
        lines.append(f"| {time_str} | {m.method} | {m.path} | {m.status_code} | {m.duration_ms:.1f}ms |")
    
    return "\n".join(lines)

def generate_html_report(report: SessionReport) -> str:
    from datetime import datetime
    
    css = """
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; background: #1e1e2e; color: #cdd6f4; }
        h1, h2 { color: #89b4fa; }
        table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #313244; }
        th { background: #252536; color: #a6adc8; }
        tr:hover { background: #2d2d44; }
        .status-2xx { color: #a6e3a1; }
        .status-3xx { color: #89b4fa; }
        .status-4xx { color: #f9e2af; }
        .status-5xx { color: #f38ba8; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
        .badge-success { background: #1e3a2e; color: #a6e3a1; }
        .badge-warning { background: #3a2e1e; color: #f9e2af; }
        .badge-danger { background: #3a1e1e; color: #f38ba8; }
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; }
        .summary-card { background: #252536; border: 1px solid #313244; border-radius: 8px; padding: 16px; }
        .summary-card .value { font-size: 2rem; font-weight: 700; }
        .summary-card .label { color: #a6adc8; font-size: 0.85rem; }
    </style>
    """
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tunnel It Report - {report.tunnel_id}</title>
    {css}
</head>
<body>
    <h1>Tunnel It Session Report</h1>
    
    <div class="summary-grid">
        <div class="summary-card"><div class="value">{report.summary.total_requests}</div><div class="label">Total Requests</div></div>
        <div class="summary-card"><div class="value">{report.summary.by_status.get('2xx', 0)}</div><div class="label">2xx Success</div></div>
        <div class="summary-card"><div class="value">{report.summary.by_status.get('4xx', 0)}</div><div class="label">4xx Errors</div></div>
        <div class="summary-card"><div class="value">{report.summary.by_status.get('5xx', 0)}</div><div class="label">5xx Errors</div></div>
        <div class="summary-card"><div class="value">{report.summary.avg_duration_ms:.1f}ms</div><div class="label">Avg Latency</div></div>
        <div class="summary-card"><div class="value">{report.summary.p95_duration_ms:.1f}ms</div><div class="label">P95 Latency</div></div>
        <div class="summary-card"><div class="value">{report.summary.slow_count}</div><div class="label">Slow (>2s)</div></div>
        <div class="summary-card"><div class="value">{report.summary.error_count}</div><div class="label">Total Errors</div></div>
    </div>
    
    <h2>Session Info</h2>
    <table>
        <tr><th>Tunnel ID</th><td>{report.tunnel_id}</td></tr>
        <tr><th>Public URL</th><td><a href="{report.public_url}" target="_blank">{report.public_url}</a></td></tr>
        <tr><th>Local Port</th><td>{report.local_port}</td></tr>
        <tr><th>Started</th><td>{report.started_at}</td></tr>
        <tr><th>Ended</th><td>{report.ended_at or 'N/A'}</td></tr>
    </table>
    
    <h2>Top Paths</h2>
    <table>
        <tr><th>Path</th><th>Count</th></tr>
"""
    for path, count in report.summary.top_paths:
        html += f"        <tr><td>{path}</td><td>{count}</td></tr>\n"
    
    html += """    </table>
    
    <h2>Top Errors</h2>
    <table>
        <tr><th>Path</th><th>Count</th></tr>
"""
    for path, count in report.summary.top_errors:
        html += f"        <tr><td>{path}</td><td>{count}</td></tr>\n"
    
    html += """    </table>
    
    <h2>All Requests</h2>
    <table>
        <tr><th>Time</th><th>Method</th><th>Path</th><th>Status</th><th>Duration</th></tr>
"""
    for m in report.metrics:
        time_str = m.timestamp.strftime("%H:%M:%S")
        status_class = f"status-{m.status_code // 100}xx"
        html += f"        <tr><td>{time_str}</td><td>{m.method}</td><td>{m.path}</td><td class='{status_class}'>{m.status_code}</td><td>{m.duration_ms:.1f}ms</td></tr>\n"
    
    html += """    </table>
</body>
</html>"""
    
    return html
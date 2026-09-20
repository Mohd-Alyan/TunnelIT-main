import json
from datetime import datetime
from flask import Flask, Response, render_template, jsonify, request
from tunnel_it.metrics import MetricsCollector, SessionReport


def create_app(metrics_collector: MetricsCollector) -> Flask:
    app = Flask(__name__, 
                template_folder="templates",
                static_folder="static")

    @app.route("/")
    def index():
        return render_template("dashboard.html", 
                               tunnel_id=metrics_collector.tunnel_id,
                               public_url=metrics_collector.public_url,
                               local_port=metrics_collector.local_port)

    @app.route("/events")
    def events():
        q = metrics_collector.subscribe()
        def stream():
            try:
                while True:
                    data = q.get()
                    yield f"data: {data}\n\n"
            except GeneratorExit:
                metrics_collector.unsubscribe(q)
        return Response(stream(), mimetype="text/event-stream")

    @app.route("/api/report")
    def api_report():
        report = metrics_collector.get_current_report()
        return jsonify(report.model_dump(mode="json"))

    @app.route("/api/history")
    def api_history():
        reports = MetricsCollector.list_reports()
        return jsonify(reports)

    @app.route("/api/report/<report_id>")
    def api_report_detail(report_id: str):
        report = MetricsCollector.load_report(report_id)
        if not report:
            return jsonify({"error": "Report not found"}), 404
        return jsonify(report.model_dump(mode="json"))

    return app


def run_dashboard(metrics_collector: MetricsCollector, host: str = "127.0.0.1", port: int = 0) -> tuple:
    from tunnel_it.metrics import find_free_port
    import threading
    
    if port == 0:
        port = find_free_port(host)
    
    app = create_app(metrics_collector)
    
    def run():
        app.run(host=host, port=port, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    
    import time
    time.sleep(0.5)
    
    dashboard_url = f"http://{host}:{port}"
    return thread, dashboard_url
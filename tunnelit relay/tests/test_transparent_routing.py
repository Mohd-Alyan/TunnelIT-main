from fastapi.testclient import TestClient
from app import app
from relay.registry import registry, Tunnel
import pytest

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_teardown():
    # Mock a tunnel for testing routing
    class MockWS:
        async def send_text(self, data):
            pass
    class MockFuture:
        def __init__(self, data):
            self.data = data
        def done(self): return True
        def result(self): return self.data
        def set_result(self, r): pass
        def set_exception(self, e): pass
        def add_done_callback(self, cb): pass
        def remove_done_callback(self, cb): pass
        def cancel(self): pass
        def cancelled(self): return False
        def exception(self): return None
        def __await__(self):
            yield
            return self.data

    tunnel = Tunnel(tunnel_id="TESTID", websocket=MockWS(), target_port=5000)
    
    # Overwrite add_request to inject mock future immediately
    def mock_add_request(request_id):
        req = type("Pending", (), {"future": MockFuture({
            "status": 200,
            "headers": {"content-type": "text/html", "location": "/redirected"},
            "body": "b2s="
        })})()
        tunnel.pending_requests[request_id] = req
        return req
    
    tunnel.add_request = mock_add_request
    registry.register(tunnel)
    
    yield
    
    registry.remove("TESTID")

def test_html_document():
    response = client.get("/t/TESTID/")
    assert response.status_code == 200
    assert response.text == "ok"
    assert "active_tunnel" in response.cookies
    assert response.cookies["active_tunnel"] == "TESTID"

def test_css_asset_referer():
    response = client.get("/static/style.css", headers={"Referer": "http://testserver/t/TESTID/"})
    assert response.status_code == 200
    assert response.text == "ok"

def test_javascript_asset_cookie():
    response = client.get("/static/script.js", cookies={"active_tunnel": "TESTID"})
    assert response.status_code == 200
    assert response.text == "ok"

def test_redirect_rewriting():
    response = client.get("/t/TESTID/login")
    assert response.headers.get("location") == "/t/TESTID/redirected"

def test_404_no_context():
    client.cookies.clear()
    response = client.get("/static/style.css")
    assert response.status_code == 404

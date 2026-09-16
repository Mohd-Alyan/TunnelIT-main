import pytest
import asyncio
import base64
import json
from fastapi.testclient import TestClient

from app import app
from relay.registry import registry

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_registry():
    # Clear registry before each test
    registry._tunnels.clear()
    yield

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_status_empty():
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "running", "active_tunnels": 0}

def test_unknown_tunnel_returns_404():
    response = client.get("/t/unknown-id/some/path")
    assert response.status_code == 404

def test_websocket_registration():
    with client.websocket_connect("/ws") as websocket:
        # Register
        websocket.send_json({"type": "register", "port": 8080})
        
        # Should receive registered message
        resp = websocket.receive_json()
        assert resp["type"] == "registered"
        assert "tunnel_id" in resp
        assert "public_url" in resp
        
        # Status should show 1 active tunnel
        status_resp = client.get("/status")
        assert status_resp.json()["active_tunnels"] == 1

@pytest.mark.asyncio
async def test_http_routing():
    from relay.registry import Tunnel, registry
    from httpx import AsyncClient, ASGITransport
    
    class MockWebsocket:
        def __init__(self):
            self.sent_messages = []
            
        async def send_text(self, text):
            self.sent_messages.append(text)
            msg = json.loads(text)
            req_id = msg["request_id"]
            
            body_str = "Hello World"
            body_b64 = base64.b64encode(body_str.encode()).decode()
            
            for t in registry._tunnels.values():
                if req_id in t.pending_requests:
                    t.resolve_request(req_id, {
                        "status": 201,
                        "headers": {"X-Response": "ResValue"},
                        "body": body_b64
                    })
                    
    tunnel = Tunnel("test-tunnel", MockWebsocket(), 8080)
    registry.register(tunnel)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/t/test-tunnel/api/test?query=param", headers={"X-Custom": "Value"})
        
    assert response.status_code == 201
    assert response.headers.get("x-response") == "ResValue"
    assert response.text == "Hello World"
    
    ws_mock = tunnel.websocket
    assert len(ws_mock.sent_messages) == 1
    ws_req = json.loads(ws_mock.sent_messages[0])
    assert ws_req["type"] == "request"
    assert ws_req["method"] == "GET"
    assert ws_req["path"] == "/api/test"
    assert ws_req["query"] == "query=param"
    assert ws_req["headers"].get("x-custom") == "Value"

@pytest.mark.asyncio
async def test_request_timeout(monkeypatch):
    from relay.config import settings
    monkeypatch.setattr(settings, "REQUEST_TIMEOUT", 0.1)
    from relay.registry import Tunnel, registry
    from httpx import AsyncClient, ASGITransport
    
    class MockWebsocket:
        async def send_text(self, text):
            pass # Do not resolve to trigger timeout
            
    tunnel = Tunnel("timeout-tunnel", MockWebsocket(), 8080)
    registry.register(tunnel)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        response = await ac.get("/t/timeout-tunnel/timeout")
        
    assert response.status_code == 504

def test_malformed_registration():
    with pytest.raises(Exception): # starlette.websockets.WebSocketDisconnect
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"type": "invalid", "port": 8080})
            websocket.receive_json() # Should close

def test_invalid_json_registration():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws") as websocket:
            websocket.send_text("not json")
            websocket.receive_text() # Should close

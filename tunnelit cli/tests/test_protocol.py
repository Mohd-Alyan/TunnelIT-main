import pytest
from tunnel_it.protocol import RegisterMessage, RequestMessage, ResponseMessage

def test_register_message():
    msg = RegisterMessage(port=8000)
    assert msg.type == "register"
    assert msg.port == 8000
    
def test_request_message():
    msg = RequestMessage(
        request_id="req-123",
        method="GET",
        path="/api",
        query="q=1",
        headers={"Host": "localhost"}
    )
    assert msg.type == "request"
    assert msg.request_id == "req-123"
    assert msg.body_encoding == "base64"
    assert msg.body == ""

def test_response_message():
    msg = ResponseMessage(
        request_id="req-123",
        status=200,
        headers={"Content-Type": "text/plain"},
        body="dGVzdA=="
    )
    assert msg.type == "response"
    assert msg.status == 200

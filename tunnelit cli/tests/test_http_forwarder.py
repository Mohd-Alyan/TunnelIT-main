import pytest
import base64
from tunnel_it.http_forwarder import HTTPForwarder
from tunnel_it.protocol import RequestMessage
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_forwarder_success():
    forwarder = HTTPForwarder(8000)
    req = RequestMessage(
        request_id="req-1",
        method="POST",
        path="/test",
        query="foo=bar",
        headers={"X-Test": "1"},
        body=base64.b64encode(b"hello").decode('utf-8')
    )
    
    mock_resp = AsyncMock()
    mock_resp.status_code = 201
    mock_resp.headers = {"X-Resp": "2"}
    mock_resp.content = b"world"
    
    with patch.object(forwarder.client, 'request', return_value=mock_resp) as mock_req:
        resp = await forwarder.forward(req)
        
        mock_req.assert_called_once()
        kwargs = mock_req.call_args.kwargs
        assert kwargs['method'] == "POST"
        assert kwargs['url'] == "http://127.0.0.1:8000/test?foo=bar"
        assert kwargs['headers'] == {"X-Test": "1"}
        assert kwargs['content'] == b"hello"
        
        assert resp.status == 201
        assert resp.headers == {"X-Resp": "2"}
        assert base64.b64decode(resp.body) == b"world"
        
    await forwarder.close()

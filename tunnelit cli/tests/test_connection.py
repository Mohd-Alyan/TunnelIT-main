import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from tunnel_it.connection import TunnelConnection
from tunnel_it.protocol import RequestMessage, ResponseMessage

@pytest.mark.asyncio
async def test_connection_message_loop():
    conn = TunnelConnection(8000)
    conn.running = True
    
    mock_ws = AsyncMock()
    mock_ws.closed = False
    
    req = RequestMessage(
        request_id="req-1",
        method="GET",
        path="/",
        query="",
        headers={},
        body=""
    )
    
    mock_ws.recv.side_effect = [
        req.model_dump_json(),
        Exception("Stop loop")
    ]
    
    conn.ws = mock_ws
    
    resp = ResponseMessage(
        request_id="req-1",
        status=200,
        headers={},
        body=""
    )
    
    with patch.object(conn.forwarder, 'forward', return_value=resp) as mock_fwd:
        await conn._message_loop()
        
        # Wait for the task to run
        await asyncio.sleep(0.1)
        
        mock_fwd.assert_called_once()
        mock_ws.send.assert_called_once()
        sent_data = mock_ws.send.call_args[0][0]
        assert "req-1" in sent_data
        
    await conn.stop()

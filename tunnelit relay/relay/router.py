import asyncio
import base64
from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import JSONResponse

from relay.registry import registry
from relay.models import RequestMessage
from relay.utils import generate_request_id
from relay.config import settings
from relay.logging_config import logger

http_router = APIRouter()

# Ignore hop-by-hop headers
HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"
}

@http_router.api_route("/t/{tunnel_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
async def handle_tunnel_request(tunnel_id: str, path: str, request: Request):
    tunnel = registry.get(tunnel_id)
    if not tunnel:
        logger.warning(f"Request for unknown tunnel: {tunnel_id}")
        raise HTTPException(status_code=404, detail="Tunnel not found")
        
    request_id = generate_request_id()
    
    # Extract headers
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in HOP_BY_HOP_HEADERS:
            headers[k] = v
            
    # Extract body
    body_bytes = await request.body()
    body_b64 = base64.b64encode(body_bytes).decode('utf-8')
    
    # Query params
    query_string = request.url.query
    
    # Prepare message
    req_msg = RequestMessage(
        request_id=request_id,
        method=request.method,
        path=f"/{path}",
        query=query_string,
        headers=headers,
        body_encoding="base64",
        body=body_b64
    )
    
    # Register pending request
    pending_req = tunnel.add_request(request_id)
    
    try:
        # Send to CLI
        await tunnel.websocket.send_text(req_msg.model_dump_json())
        logger.info(f"Forwarded request {request_id} to tunnel {tunnel_id}")
        
        # Wait for response with timeout
        try:
            response_data = await asyncio.wait_for(pending_req.future, timeout=settings.REQUEST_TIMEOUT)
        except asyncio.TimeoutError:
            logger.error(f"Request {request_id} timed out for tunnel {tunnel_id}")
            tunnel.pending_requests.pop(request_id, None)
            return JSONResponse(status_code=504, content={"detail": "Gateway Timeout"})
            
        # Parse response
        status = response_data.get("status", 500)
        resp_headers = response_data.get("headers", {})
        resp_body_b64 = response_data.get("body", "")
        
        try:
            resp_body_bytes = base64.b64decode(resp_body_b64)
        except Exception as e:
            logger.error(f"Failed to decode response body for request {request_id}: {e}")
            return JSONResponse(status_code=502, content={"detail": "Bad Gateway"})
            
        # Filter hop-by-hop headers from response
        filtered_headers = {k: v for k, v in resp_headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
        
        return Response(content=resp_body_bytes, status_code=status, headers=filtered_headers)
        
    except Exception as e:
        logger.error(f"Error handling request {request_id} for tunnel {tunnel_id}: {e}")
        tunnel.pending_requests.pop(request_id, None)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

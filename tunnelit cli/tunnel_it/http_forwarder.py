import base64
import httpx
from .protocol import RequestMessage, ResponseMessage
from .config import settings
from .logging_config import logger

HOP_BY_HOP_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailer", "transfer-encoding", "upgrade"
}

class HTTPForwarder:
    def __init__(self, target_port: int):
        self.target_port = target_port
        self.client = httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT)

    async def close(self):
        await self.client.aclose()

    async def forward(self, req_msg: RequestMessage) -> ResponseMessage:
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
                return ResponseMessage(
                    request_id=req_msg.request_id,
                    status=400,
                    headers={},
                    body=base64.b64encode(b"Bad Request: invalid base64 body").decode('utf-8')
                )

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
            
            return ResponseMessage(
                request_id=req_msg.request_id,
                status=response.status_code,
                headers=resp_headers,
                body=resp_body_b64
            )
        except httpx.RequestError as e:
            logger.error(f"Error forwarding request {req_msg.request_id} to local service: {e}")
            return ResponseMessage(
                request_id=req_msg.request_id,
                status=502,
                headers={},
                body=base64.b64encode(b"Bad Gateway: local service unavailable").decode('utf-8')
            )

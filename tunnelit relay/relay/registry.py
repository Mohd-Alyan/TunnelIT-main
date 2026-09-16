import asyncio
from typing import Dict, Optional
from fastapi import WebSocket
from relay.logging_config import logger

class PendingRequest:
    def __init__(self, request_id: str):
        self.request_id = request_id
        self.future = asyncio.Future()

class Tunnel:
    def __init__(self, tunnel_id: str, websocket: WebSocket, target_port: int):
        self.tunnel_id = tunnel_id
        self.websocket = websocket
        self.target_port = target_port
        self.pending_requests: Dict[str, PendingRequest] = {}
        
    def add_request(self, request_id: str) -> PendingRequest:
        req = PendingRequest(request_id)
        self.pending_requests[request_id] = req
        return req
        
    def resolve_request(self, request_id: str, response_data: dict):
        if request_id in self.pending_requests:
            req = self.pending_requests.pop(request_id)
            if not req.future.done():
                req.future.set_result(response_data)
                
    def fail_all_requests(self, exception: Exception):
        for req in self.pending_requests.values():
            if not req.future.done():
                req.future.set_exception(exception)
        self.pending_requests.clear()

class TunnelRegistry:
    def __init__(self):
        self._tunnels: Dict[str, Tunnel] = {}
        
    def register(self, tunnel: Tunnel):
        self._tunnels[tunnel.tunnel_id] = tunnel
        logger.info(f"Registered tunnel {tunnel.tunnel_id}")
        
    def get(self, tunnel_id: str) -> Optional[Tunnel]:
        return self._tunnels.get(tunnel_id)
        
    def remove(self, tunnel_id: str):
        if tunnel_id in self._tunnels:
            tunnel = self._tunnels.pop(tunnel_id)
            tunnel.fail_all_requests(Exception(f"Tunnel {tunnel_id} disconnected"))
            logger.info(f"Removed tunnel {tunnel_id}")
            
    def exists(self, tunnel_id: str) -> bool:
        return tunnel_id in self._tunnels
        
    def list_active(self) -> list[str]:
        return list(self._tunnels.keys())

    def active_count(self) -> int:
        return len(self._tunnels)

registry = TunnelRegistry()

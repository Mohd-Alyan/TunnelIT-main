import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from typing import Optional, Any
from .protocol import RegisterMessage, RegisteredMessage, RequestMessage, ResponseMessage
from .http_forwarder import HTTPForwarder
from .config import settings
from .logging_config import logger
from .display import display_tunnel_info, log_request
from .metrics import MetricsCollector
from .dashboard.app import run_dashboard


class TunnelConnection:
    def __init__(self, target_port: int):
        self.target_port = target_port
        self.metrics_collector = MetricsCollector("", "", target_port)
        self.forwarder = HTTPForwarder(target_port, self.metrics_collector)
        self.ws: Any = None
        self.active_tasks = set()
        self.running = False
        self.tunnel_id: Optional[str] = None
        self.public_url: Optional[str] = None
        self.dashboard_thread = None
        self.dashboard_url: Optional[str] = None

    async def _handle_request(self, req_msg: RequestMessage):
        resp_msg = await self.forwarder.forward(req_msg)
        log_request(req_msg.method, req_msg.path, resp_msg.status)
        
        try:
            if self.ws:
                await self.ws.send(resp_msg.model_dump_json())
        except ConnectionClosed:
            pass  # Normal disconnect
        except Exception as e:
            logger.error(f"Failed to send response for {req_msg.request_id}: {e}")

    async def _message_loop(self):
        while self.running and self.ws:
            try:
                data = await self.ws.recv()
                msg_data = json.loads(data)
                
                if msg_data.get("type") == "request":
                    req_msg = RequestMessage(**msg_data)
                    task = asyncio.create_task(self._handle_request(req_msg))
                    self.active_tasks.add(task)
                    task.add_done_callback(self.active_tasks.discard)
                else:
                    logger.warning(f"Unknown message type received: {msg_data.get('type')}")
                    
            except ConnectionClosed:
                logger.info("WebSocket connection closed")
                break
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                break

    async def connect(self):
        self.running = True
        while self.running:
            try:
                logger.info(f"Connecting to relay at {settings.RELAY_URL}")
                async with websockets.connect(settings.RELAY_URL) as ws:
                    self.ws = ws
                    
                    reg_msg = RegisterMessage(port=self.target_port)
                    await ws.send(reg_msg.model_dump_json())
                    
                    resp_data = await ws.recv()
                    msg_data = json.loads(resp_data)
                    
                    if msg_data.get("type") == "registered":
                        reg_resp = RegisteredMessage(**msg_data)
                        self.tunnel_id = reg_resp.tunnel_id
                        self.public_url = reg_resp.public_url
                        
                        self.metrics_collector.tunnel_id = self.tunnel_id
                        self.metrics_collector.public_url = self.public_url
                        await self.metrics_collector.start()
                        
                        if settings.DASHBOARD_ENABLED:
                            self.dashboard_thread, self.dashboard_url = run_dashboard(
                                self.metrics_collector,
                                settings.DASHBOARD_HOST,
                                settings.DASHBOARD_PORT
                            )
                        
                        display_tunnel_info(
                            self.target_port, 
                            settings.RELAY_URL, 
                            self.tunnel_id, 
                            self.public_url,
                            self.dashboard_url
                        )
                        
                        await self._message_loop()
                    else:
                        logger.error(f"Expected registered message, got: {msg_data}")
                        break
                        
            except (WebSocketException, OSError, asyncio.TimeoutError) as e:
                logger.error(f"Connection failed: {e}")
                
            if not self.running or not settings.RECONNECT_ENABLED:
                break
                
            logger.info(f"Reconnecting in {settings.RECONNECT_DELAY} seconds...")
            await asyncio.sleep(settings.RECONNECT_DELAY)
            
    async def stop(self):
        self.running = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            
        for task in self.active_tasks:
            task.cancel()
            
        await self.forwarder.close()
        
        if self.metrics_collector:
            await self.metrics_collector.stop()
            self.metrics_collector.finalize()
        
        if self.dashboard_thread:
            self.dashboard_thread.join(timeout=2)
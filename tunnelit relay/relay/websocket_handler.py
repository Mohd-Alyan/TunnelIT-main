import json
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from relay.models import RegisterMessage, RegisteredMessage, ResponseMessage
from relay.registry import registry, Tunnel
from relay.utils import generate_tunnel_id, get_public_url
from relay.logging_config import logger
from relay.config import settings

ws_router = APIRouter()

@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("New WebSocket connection accepted")
    
    tunnel_id = None
    try:
        # Wait for registration message
        data = await websocket.receive_text()
        try:
            msg_data = json.loads(data)
            if msg_data.get("type") != "register":
                logger.warning("First message was not a register message")
                await websocket.close(code=1003, reason="Expected register message")
                return
            
            register_msg = RegisterMessage(**msg_data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Invalid registration message: {e}")
            await websocket.close(code=1003, reason="Invalid registration message")
            return

        if registry.active_count() >= settings.MAX_TUNNELS:
            logger.warning("Max tunnels reached")
            await websocket.close(code=1013, reason="Max tunnels reached")
            return

        # Registration successful
        tunnel_id = generate_tunnel_id()
        tunnel = Tunnel(tunnel_id=tunnel_id, websocket=websocket, target_port=register_msg.port)
        registry.register(tunnel)
        
        public_url = get_public_url(tunnel_id)
        registered_msg = RegisteredMessage(tunnel_id=tunnel_id, public_url=public_url)
        await websocket.send_text(registered_msg.model_dump_json())
        
        # Message loop
        while True:
            data = await websocket.receive_text()
            try:
                msg_data = json.loads(data)
                if msg_data.get("type") == "response":
                    response_msg = ResponseMessage(**msg_data)
                    tunnel.resolve_request(response_msg.request_id, response_msg.model_dump())
                else:
                    logger.warning(f"Unknown message type received from {tunnel_id}: {msg_data.get('type')}")
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Invalid message received from {tunnel_id}: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for tunnel {tunnel_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket handler for tunnel {tunnel_id}: {e}")
    finally:
        if tunnel_id:
            registry.remove(tunnel_id)

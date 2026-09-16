import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from relay.config import settings
from relay.logging_config import setup_logging
from relay.websocket_handler import ws_router
from relay.router import http_router
from relay.registry import registry

setup_logging()

app = FastAPI(title="Tunnel It Relay")

@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "healthy"})

@app.get("/status")
async def get_status():
    return JSONResponse(content={
        "status": "running",
        "active_tunnels": registry.active_count()
    })

app.include_router(ws_router)
app.include_router(http_router)

if __name__ == "__main__":
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=False)

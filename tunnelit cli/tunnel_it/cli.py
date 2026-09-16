import asyncio
import typer
import sys
import httpx
from rich.console import Console
from .connection import TunnelConnection
from .logging_config import setup_logging

app = typer.Typer(help="Tunnel It CLI Agent", no_args_is_help=True)
console = Console()

@app.callback()
def callback():
    """Tunnel It CLI Agent"""
    pass

async def check_local_service(port: int) -> bool:
    url = f"http://127.0.0.1:{port}"
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            await client.get(url)
            return True
        except httpx.RequestError:
            return False

async def run_tunnel(port: int):
    setup_logging()
    
    console.print(f"Checking local service at http://127.0.0.1:{port}...", style="dim")
    is_up = await check_local_service(port)
    if not is_up:
        console.print("[yellow]Warning: Local service unavailable[/yellow]")
        console.print(f"Could not connect to 127.0.0.1:{port}.")
        console.print("Make sure your HTTP server is running. Tunnel will still be created.\n")
        
    connection = TunnelConnection(port)
    
    # We create a task for the connection to allow graceful shutdown
    # but since asyncio.run doesn't let us easily catch KeyboardInterrupt inside
    # we just await it directly and rely on KeyboardInterrupt to stop the event loop
    try:
        await connection.connect()
    except asyncio.CancelledError:
        pass
    finally:
        console.print("\nShutting down tunnel...", style="yellow")
        await connection.stop()
        console.print("Connection closed.", style="yellow")

@app.command()
def expose(port: int = typer.Argument(..., min=1, max=65535, help="Local port to expose")):
    try:
        asyncio.run(run_tunnel(port))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    app()

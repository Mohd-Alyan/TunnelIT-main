import asyncio
import typer
import sys
import httpx
import time
from urllib.parse import urlparse
from rich.console import Console
from .connection import TunnelConnection
from .logging_config import setup_logging
from .config import settings

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

def get_http_url(relay_url: str) -> str:
    parsed = urlparse(relay_url)
    scheme = "https" if parsed.scheme in ("wss", "https") else "http"
    # Ensure no trailing path like /ws by only taking netloc
    return f"{scheme}://{parsed.netloc}"

async def run_wakeup():
    http_url = get_http_url(settings.RELAY_URL)
    health_url = f"{http_url}/health"
    
    console.print("Waking Tunnel It relay...")
    console.print("Relay:")
    console.print(http_url)
    console.print("\nWaiting for relay to become ready...")
    
    start_time = time.time()
    attempt = 1
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            console.print(f"Attempt {attempt}")
            try:
                response = await client.get(health_url)
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if data.get("status") == "healthy":
                            console.print("\nTunnel It relay is up.")
                            console.print("Health:")
                            console.print("healthy")
                            return
                    except Exception:
                        pass
            except Exception:
                # Catch connection errors, timeouts, etc.
                pass
            
            elapsed = time.time() - start_time
            if elapsed >= settings.WAKEUP_TIMEOUT:
                console.print(f"\nUnable to wake relay within {settings.WAKEUP_TIMEOUT} seconds.")
                sys.exit(1)
            
            await asyncio.sleep(settings.WAKEUP_INTERVAL)
            attempt += 1

@app.command()
def wakeup():
    """Wake the Render relay"""
    try:
        asyncio.run(run_wakeup())
    except KeyboardInterrupt:
        pass

@app.command()
def changerelay(url: str = typer.Argument(..., help="The new relay URL")):
    """Change the persistent relay server"""
    from .config import USER_CONFIG_PATH, env_file_path
    
    # Create directory if it doesn't exist
    USER_CONFIG_PATH.mkdir(parents=True, exist_ok=True)
    
    # Read existing config to keep other variables
    lines = []
    if env_file_path.exists():
        with open(env_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    # Update RELAY_URL
    new_lines = []
    found = False
    for line in lines:
        if line.strip().startswith("RELAY_URL") and "=" in line:
            new_lines.append(f"RELAY_URL={url}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"RELAY_URL={url}\n")
        
    with open(env_file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
        
    console.print(f"Relay URL updated to [bold]{url}[/bold]")

if __name__ == "__main__":
    app()

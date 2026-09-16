from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import datetime

console = Console()

def display_tunnel_info(local_port: int, public_url: str):
    content = Text()
    content.append("+ Connected\n", style="green")
    content.append("+ Tunnel established\n\n", style="green")
    
    content.append("Local:\n", style="bold")
    content.append(f"  http://127.0.0.1:{local_port}\n\n", style="cyan")
    
    content.append("Public URL:\n", style="bold")
    content.append(f"  {public_url}\n\n", style="magenta")
    
    content.append("Status: ", style="bold")
    content.append("ACTIVE", style="green bold")
    
    panel = Panel(
        content,
        title="[bold blue]Tunnel It[/bold blue]",
        expand=False,
        border_style="blue"
    )
    console.print(panel)
    console.print("Press Ctrl+C to stop\n", style="dim")

def log_request(method: str, path: str, status: int):
    time_str = datetime.datetime.now().strftime("%H:%M:%S")
    
    status_color = "green"
    if status >= 400:
        status_color = "red"
    elif status >= 300:
        status_color = "yellow"
        
    console.print(f"{time_str}  {method:7} {path:40} [{status_color}]{status}[/]")

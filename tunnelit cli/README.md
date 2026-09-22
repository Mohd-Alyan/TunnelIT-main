# Tunnel It CLI

Tunnel It CLI is a lightweight terminal application that allows you to expose a local HTTP service through the Tunnel It public relay.

## Installation

1. Clone the repository and navigate to the `tunnelit cli` directory.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install the CLI:
   ```bash
   pip install -e .
   ```

## Usage

To wake the Render relay (if it has been asleep):
```bash
tunnel-it wakeup
```

To expose a local port (e.g., 8000), simply run:
```bash
tunnel-it expose 8000
```

Recommended usage:
```bash
# Wake the Render relay
tunnel-it wakeup

# Expose local service
tunnel-it expose 5000
```

The CLI will dynamically register with the configured relay, obtain a public URL and tunnel ID, and then seamlessly forward incoming HTTP requests to your local service.

## Commands

| Command | Description |
|---------|-------------|
| `tunnel-it expose <port>` | Expose a local HTTP service on the given port |
| `tunnel-it wakeup` | Wake the configured relay and wait until it is ready |
| `tunnel-it changerelay <url>` | Change the persistent relay server |
| `tunnel-it report list` | List all saved session reports |
| `tunnel-it report show <id> [--format json\|md\|html]` | Show a specific report |
| `tunnel-it report export <id> --output <file> [--format json\|md\|html]` | Export a report to a file |
| `tunnel-it --help` | Show complete CLI help |

## Configuration

You can configure the application using environment variables. Create a `.env` file based on `.env.example` in `~/.tunnelit/config.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `RELAY_URL` | `wss://tunnelit-main.onrender.com/ws` | WebSocket URL of the Tunnel It relay |
| `REQUEST_TIMEOUT` | `30` | Timeout for forwarding requests to local service (seconds) |
| `RECONNECT_ENABLED` | `True` | Automatically reconnect on connection loss |
| `RECONNECT_DELAY` | `5` | Delay before reconnect attempt (seconds) |
| `LOG_LEVEL` | `INFO` | Application log verbosity |
| `MAX_RESPONSE_SIZE` | `5242880` | Maximum response body size (5MB) |
| `WAKEUP_TIMEOUT` | `90` | Maximum time to wait for relay wakeup (seconds) |
| `WAKEUP_INTERVAL` | `3` | Polling interval during wakeup (seconds) |
| `DASHBOARD_ENABLED` | `True` | Enable live traffic dashboard |
| `DASHBOARD_HOST` | `127.0.0.1` | Dashboard bind address |
| `DASHBOARD_PORT` | `0` | Dashboard port (0 = auto-pick free port) |

## Architecture

The system works as follows:

- **CLI → WebSocket → Relay**: The CLI establishes a persistent WebSocket connection with the relay. It registers its port and receives requests asynchronously.
- **CLI → HTTP → Local Service**: Upon receiving a request from the relay, the CLI reconstructs it locally using an asynchronous HTTP client, forwards it to the specified local HTTP service, and then relays the response back via the WebSocket connection.
- **Dashboard**: Optional Flask-based live dashboard showing real-time traffic, request/response details, and latency metrics (enabled by default).
- **Metrics**: Automatic collection of request/response metrics with session reports saved to `~/.tunnelit/reports/`.

## Protocol

The relay and CLI communicate using JSON messages over a WebSocket connection.

1. **Registration**: The CLI sends a `{"type": "register", "port": <port>}` message.
2. **Confirmation**: The relay responds with a `{"type": "registered", "tunnel_id": "<id>", "public_url": "<url>"}` message.
3. **Requests**: The relay forwards incoming HTTP requests as `{"type": "request", ...}` containing the method, path, headers, query string, and base64-encoded body.
4. **Responses**: The CLI sends back HTTP responses as `{"type": "response", ...}` containing the corresponding request ID, status code, headers, and base64-encoded body.

## Error Handling & Reconnection

The CLI gracefully handles various errors:
- If the local service is down or slow, the CLI returns a `502 Bad Gateway` or `504 Gateway Timeout` to the remote visitor without crashing.
- If the WebSocket connection drops, the CLI will automatically attempt to reconnect and re-register if `RECONNECT_ENABLED` is true.
- Exponential backoff and configurable retry logic.

## Security Considerations

The CLI forwards requests **only** to the locally configured target service (`127.0.0.1:<PORT>`). It does not allow the relay to instruct it to connect to arbitrary remote addresses, preventing it from being used as an SSRF-style arbitrary network proxy.

## Testing

To run the automated tests:
```bash
python -m pytest tests/
```

Tests cover protocol handling, HTTP forwarding, connection management, and CLI commands.
# Tunnel It Relay

Tunnel It Relay is a lightweight, asynchronous Python web service that acts as a public intermediary between internet visitors and local services running on development machines. It accepts persistent WebSocket connections from Tunnel It CLI clients and exposes public HTTP endpoints, routing incoming HTTP traffic to the appropriate local port on the client's machine.

## Architecture

```text
Internet Visitor → HTTP → Relay → WebSocket → CLI → HTTP → Local Service
```

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running Locally

To start the server, run:
```bash
python app.py
```
Alternatively, you can run Uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check - returns `{"status": "healthy"}` |
| `/status` | GET | Relay status and active tunnel count |
| `/t/<tunnel_id>/...` | GET/POST/... | Proxy HTTP traffic to registered tunnel |
| `/ws` | WS | WebSocket endpoint for CLI connections |

## Configuration

Configuration is managed via environment variables. You can provide these in a `.env` file (see `.env.example`).

* `HOST`: The interface to bind the server to (default: `0.0.0.0`).
* `PORT`: The port the server listens on (default: `8000`).
* `PUBLIC_BASE_URL`: The public URL of the relay, used to generate dynamic tunnel links (default: `http://localhost:8000`).
* `TUNNEL_ID_LENGTH`: The length of the dynamically generated tunnel ID (default: `8`).
* `REQUEST_TIMEOUT`: Timeout in seconds when waiting for a response from the CLI (default: `30.0`).
* `MAX_TUNNELS`: Maximum number of allowed simultaneous tunnels (default: `100`).
* `LOG_LEVEL`: Logging verbosity level, e.g., `INFO`, `DEBUG` (default: `INFO`).

## Protocol

The CLI communicates with the Relay via WebSocket JSON messages.

### Registration

**CLI → Relay**
```json
{
  "type": "register",
  "port": 8000
}
```

### Registration Response

**Relay → CLI**
```json
{
  "type": "registered",
  "tunnel_id": "a8F3kP91",
  "public_url": "http://localhost:8000/t/a8F3kP91"
}
```

### Request

**Relay → CLI**
```json
{
  "type": "request",
  "request_id": "req_5f2b...",
  "method": "GET",
  "path": "/api/data",
  "query": "param=1",
  "headers": {"User-Agent": "curl/7.68.0"},
  "body_encoding": "base64",
  "body": ""
}
```

### Response

**CLI → Relay**
```json
{
  "type": "response",
  "request_id": "req_5f2b...",
  "status": 200,
  "headers": {"Content-Type": "application/json"},
  "body_encoding": "base64",
  "body": "eyJrZXkiOiAidmFsdWUifQ=="
}
```

### Errors

- Request timeouts trigger a `504 Gateway Timeout`.
- Non-existent or disconnected tunnels trigger a `404 Not Found`.
- Malformed connections or invalid protocol messages will cause the WebSocket to disconnect.

## Testing

To run the automated tests, ensure you are in the active virtual environment and run:
```bash
python -m pytest tests/
```
*(Tests utilize `pytest`, `httpx`, and `pytest-asyncio` to comprehensively test the relay routing and cleanup logic without hard dependencies on an actual CLI).*

## Limitations

As an MVP, this relay implementation has the following limitations:
* **Single Instance**: The in-memory tunnel registry does not support multi-process or multi-server scaling without external persistence (e.g., Redis).
* **HTTP-Focused**: Intended for HTTP/HTTPS forwarding; raw TCP or UDP tunnels are not supported.
* **No Authentication**: The MVP currently lacks authentication mechanisms for clients creating tunnels.
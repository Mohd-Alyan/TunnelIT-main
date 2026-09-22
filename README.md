<h1 align="center">
  🚇 Tunnel It
</h1>

<p align="center">
  <b>A lightweight, secure reverse HTTP tunneling system built with Python, FastAPI, and WebSockets.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/FastAPI-0.110+-00a393.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Typer-CLI-black.svg" alt="Typer">
  <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
</p>

---

## 📖 Overview

**Tunnel It** allows you to expose a local HTTP service (running on your laptop behind NAT/firewalls) to the public internet using a remote relay server.

Instead of configuring complex port forwarding on your router, you simply run the **Tunnel It CLI**, which establishes a persistent WebSocket connection to your public **Tunnel It Relay**. The relay generates a dynamic public URL and transparently proxies incoming web traffic safely and concurrently back down to your local machine.

### ✨ Key Features

- **Transparent Proxying:** Seamlessly routes HTML, CSS, JavaScript, Images, and APIs without requiring any rewrites to your local application code.
- **Robust Routing:** Uses intelligent `Referer` extraction and Cookie-fallback mechanisms to preserve the tunnel namespace for root-relative assets flawlessly.
- **Concurrent & Asynchronous:** Safely multiplexes concurrent requests over a single WebSocket connection without head-of-line blocking.
- **Secure Isolation:** The CLI natively enforces strict SSRF protection (bound strictly to `127.0.0.1:<PORT>`), discarding arbitrary external connection attempts.
- **Auto-Healing:** Built-in connection lifecycle management. Dropped Wi-Fi or relay restarts trigger graceful back-off and reconnection without leaking memory or zombie tasks.
- **Live Dashboard:** Real-time traffic monitoring with request/response inspection, latency metrics, and error tracking.
- **Session Reports:** Automatic metrics collection with JSON/HTML/Markdown export for debugging and sharing.
- **Relay Wakeup:** Built-in helper to wake sleeping serverless/free-tier relay infrastructure before tunneling.

---

## 🏗️ Architecture

```text
External Browser
       │
       │ HTTPS
       ▼
Tunnel It Relay (e.g., Render)
       │
       │ Persistent WSS (WebSocket)
       ▼
Tunnel It CLI (Your Laptop)
       │
       │ HTTP
       ▼
127.0.0.1:<USER_PORT> (Local App)
```

The repository consists of four components:
1. `tunnelit relay/`: The public FastAPI gateway server.
2. `tunnelit cli/`: The local Typer-based command-line agent.
3. `demo app/`: A simple Flask website to test the tunnel.
4. `tunnelit site/`: A landing page for the project.

---

## 🚀 1. Relay Server Setup

The Relay is the public-facing gateway. It requires Python 3.9+.

### Local Development

```bash
cd "tunnelit relay"
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

The relay will start on `http://0.0.0.0:8000`.

### ☁️ Production Deployment (Render)

Deploying the relay to Render (or a similar PaaS) is fully supported and recommended.

1. Create a new **Web Service** on Render.
2. Point it to your repository.
3. Use the following configuration:
   - **Root Directory**: `tunnelit relay`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Set the **Environment Variable**:
   - `PUBLIC_BASE_URL`: `https://YOUR_APP_NAME.onrender.com`

### Relay Endpoints

- `GET /health` - Health check endpoint (returns `{"status": "healthy"}`)
- `GET /status` - Returns relay status and active tunnel count
- `GET /t/<tunnel_id>/...` - Proxies HTTP traffic to registered tunnels
- `GET /ws` - WebSocket endpoint for CLI connections

### Relay Configuration

Environment variables (can be set in `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `0.0.0.0` | Interface to bind |
| `PORT` | `8000` | Port to listen on |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Public URL for generating tunnel links |
| `TUNNEL_ID_LENGTH` | `8` | Length of generated tunnel IDs |
| `REQUEST_TIMEOUT` | `30` | Seconds to wait for CLI response |
| `MAX_TUNNELS` | `100` | Maximum simultaneous tunnels |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 💻 2. CLI Agent Setup

The CLI is the lightweight client installed on your local machine.

### Installation

```bash
cd "tunnelit cli"
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -e .
```

### Configuration

Tell the CLI where your deployed relay lives by exporting the `RELAY_URL` environment variable.

**Windows (PowerShell):**
```powershell
$env:RELAY_URL="wss://tunnelit-main.onrender.com/ws"
```

**Linux / macOS:**
```bash
export RELAY_URL="wss://tunnelit-main.onrender.com/ws"
```

*(If unset, it defaults to `wss://tunnelit-main.onrender.com/ws` for production use, or `ws://127.0.0.1:8000/ws` for local testing.)*

### CLI Configuration Options

Create a `.env` file in `~/.tunnelit/config.env` or use environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RELAY_URL` | `wss://tunnelit-main.onrender.com/ws` | WebSocket URL of the relay |
| `REQUEST_TIMEOUT` | `30` | Request forwarding timeout (seconds) |
| `RECONNECT_ENABLED` | `True` | Auto-reconnect on connection loss |
| `RECONNECT_DELAY` | `5` | Reconnect delay (seconds) |
| `LOG_LEVEL` | `INFO` | Log verbosity |
| `MAX_RESPONSE_SIZE` | `5242880` | Max response size (5MB) |
| `WAKEUP_TIMEOUT` | `90` | Wakeup max wait time (seconds) |
| `WAKEUP_INTERVAL` | `3` | Wakeup polling interval (seconds) |
| `DASHBOARD_ENABLED` | `True` | Enable live dashboard |
| `DASHBOARD_HOST` | `127.0.0.1` | Dashboard bind address |
| `DASHBOARD_PORT` | `0` | Dashboard port (0 = auto) |

---

## 🎮 3. Usage & Testing

### Step 1: Start a Local Service

If you don't have a local service running, use the provided demo app:

```bash
cd "demo app"
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

*(The demo runs on port `5000`)*

### Step 2: Wake the Relay (Recommended)

If your relay is on a free tier (e.g., Render), it may spin down after inactivity:

```bash
tunnel-it wakeup
```

This polls the relay's `/health` endpoint until it responds healthy.

### Step 3: Expose the Port

In a new terminal (with your CLI virtual environment activated), expose the port:

```bash
tunnel-it expose 5000
```

### Step 4: Access the Public URL

The CLI will securely register with the relay and output your connection details:

```text
+------------ Tunnel It ------------+
| Local service:                    |
| 127.0.0.1:5000                    |
|                                   |
| Relay:                            |
| wss://tunnelit-main.onrender.com/ws    |
|                                   |
| Connection status:                |
| Connected                         |
|                                   |
| Tunnel ID:                        |
| E4FTrALJ                          |
|                                   |
| Public URL:                       |
| https://tunnelit-main.onrender.com/t/E4FTrALJ/ |
|                                   |
| Dashboard:                        |
| http://127.0.0.1:54321            |
+-----------------------------------+
```

Open the **Public URL** in your browser. All requests to this public URL will be instantly routed through the WebSocket down to your local machine!

Open the **Dashboard URL** to see live traffic, request/response details, and latency metrics.

---

## 📊 4. Session Reports & Metrics

The CLI automatically collects metrics for every tunnel session. After the tunnel closes, a report is saved to `~/.tunnelit/reports/`.

### List Reports

```bash
tunnel-it report list
```

### View a Report

```bash
# JSON format (default)
tunnel-it report show <report_id>

# Human-readable markdown
tunnel-it report show <report_id> --format md

# HTML (opens in browser)
tunnel-it report show <report_id> --format html
```

### Export a Report

```bash
tunnel-it report export <report_id> --output report.html --format html
tunnel-it report export <report_id> --output report.json --format json
tunnel-it report export <report_id> --output report.md --format md
```

Reports include:
- Total requests, status code distribution
- Average latency, P95 latency, slow request count
- Top paths and top errors
- Full request timeline with timestamps

---

## 🔧 5. Command Reference

| Command | Description |
|---------|-------------|
| `tunnel-it expose <port>` | Expose a local HTTP service |
| `tunnel-it wakeup` | Wake the relay and wait until ready |
| `tunnel-it changerelay <url>` | Change the persistent relay server |
| `tunnel-it report list` | List all saved session reports |
| `tunnel-it report show <id>` | Show a specific report |
| `tunnel-it report export <id>` | Export a report to file |
| `tunnel-it --help` | Show complete CLI help |

---

## 🛡️ Security Note

The CLI restricts all forwarded requests strictly to the local loopback interface (`127.0.0.1`). It aggressively strips dangerous hop-by-hop HTTP headers and utilizes Pydantic validation across the WebSocket serialization boundary to prevent injection attacks and Server-Side Request Forgery (SSRF).

---

## 🌐 6. Project Landing Page

The `tunnelit site/` directory contains a modern landing page (`index.html`) with installation instructions, quick start guide, architecture diagram, and feature highlights. Deploy it to Vercel, Netlify, or GitHub Pages to provide a user-friendly entry point for your Tunnel It deployment.
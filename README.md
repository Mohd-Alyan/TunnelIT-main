<h1 align="center">
  🚇 Tunnel It
</h1>

<p align="center">
  <b>A lightweight, secure reverse HTTP tunneling system built with Python, FastAPI, and WebSockets.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python Version">
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

The repository consists of three independent components:
1. `tunnelit relay/`: The public FastAPI gateway server.
2. `tunnelit cli/`: The local Typer-based command-line agent.
3. `demo app/`: A simple Flask website to test the tunnel.

---

## 🚀 1. Relay Server Setup

The Relay is the public-facing gateway. It requires Python 3.10+.

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

---

## 💻 2. CLI Agent Setup

The CLI is the lightweight client installed on your local machine.

### Installation
```bash
cd "tunnelit cli"
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -e .
```

### Configuration
Tell the CLI where your deployed relay lives by exporting the `RELAY_URL` environment variable.

**Windows (PowerShell):**
```powershell
$env:RELAY_URL="wss://YOUR_APP_NAME.onrender.com/ws"
```
**Linux / macOS:**
```bash
export RELAY_URL="wss://YOUR_APP_NAME.onrender.com/ws"
```
*(If unset, it defaults to `ws://127.0.0.1:8000/ws` for local testing).*

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

### Step 2: Expose the Port
In a new terminal (with your CLI virtual environment activated), expose the port:
```bash
tunnel-it expose 5000
```

### Step 3: Access the Public URL
The CLI will securely register with the relay and output your connection details:

```text
+------------ Tunnel It ------------+
| Local service:                    |
| 127.0.0.1:5000                    |
|                                   |
| Relay:                            |
| wss://YOUR_APP.onrender.com/ws    |
|                                   |
| Connection status:                |
| Connected                         |
|                                   |
| Tunnel ID:                        |
| E4FTrALJ                          |
|                                   |
| Public URL:                       |
| https://YOUR_APP.onrender.com/t/E4FTrALJ/ |
+-----------------------------------+
```

Open the **Public URL** in your browser. All requests to this public URL will be instantly routed through the WebSocket down to your local machine!

---

## 🛡️ Security Note
The CLI restricts all forwarded requests strictly to the local loopback interface (`127.0.0.1`). It aggressively strips dangerous hop-by-hop HTTP headers and utilizes Pydantic validation across the WebSocket serialization boundary to prevent injection attacks and Server-Side Request Forgery (SSRF).

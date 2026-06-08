"""
Unified server entry point for the packaged Word AI app.

Starts two servers in one process:
- FastAPI backend on 127.0.0.1:<api_port> (HTTP, default 8000)
- Word add-in static files on localhost:<ui_port> (HTTPS, default 3443)

Usage: WordAI.exe [--api-port 8000] [--ui-port 3443]
Environment: WORD_AI_API_PORT, WORD_AI_UI_PORT
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import http.server
import ssl
import urllib.parse
from functools import partial
from pathlib import Path


def _get_package_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _find_certs(base: Path) -> tuple[Path, Path]:
    for name in (".certs", "certs"):
        cert_dir = base / name
        if cert_dir.exists():
            cert = cert_dir / "localhost.pem"
            key = cert_dir / "localhost-key.pem"
            if cert.exists() and key.exists():
                return cert, key
    raise FileNotFoundError(
        "SSL certificates not found. Run 'python scripts/generate_cert.py' first."
    )


def _port_in_use(host: str, port: int) -> bool:
    """Check if a port is already bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def _find_free_port(host: str, start: int, max_attempts: int = 10) -> int:
    """Find the next available port starting from `start`."""
    for port in range(start, start + max_attempts):
        if not _port_in_use(host, port):
            return port
    raise RuntimeError(f"No free port found in range {start}-{start + max_attempts}")


def start_https_server(
    addin_dir: Path,
    cert: Path,
    key: Path,
    api_url: str,
    port: int = 3443,
) -> threading.Thread:
    runtime_config = {
        "apiBase": api_url,
    }

    class AddinRequestHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            path = urllib.parse.urlparse(self.path).path
            if path == "/runtime-config.json":
                payload = json.dumps(runtime_config).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            super().do_GET()

    handler = partial(AddinRequestHandler, directory=str(addin_dir))

    class ReuseServer(http.server.ThreadingHTTPServer):
        allow_reuse_address = True

    if _port_in_use("localhost", port):
        print(f"[Word AI] WARNING: port {port} is in use, trying next...")
        port = _find_free_port("localhost", port + 1)

    server = ReuseServer(("localhost", port), handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(cert), keyfile=str(key))
    server.socket = context.wrap_socket(server.socket, server_side=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[Word AI] Add-in UI: https://localhost:{port}")
    print(f"[Word AI] Runtime config: {api_url}")
    return thread


def start_servers() -> None:
    parser = argparse.ArgumentParser(description="Word AI Assistant Server")
    parser.add_argument("--api-port", type=int, default=None, help="API server port (default: 8000)")
    parser.add_argument("--ui-port", type=int, default=None, help="HTTPS UI server port (default: 3443)")
    args = parser.parse_args()

    api_host = "127.0.0.1"
    ui_host = "localhost"

    api_port = args.api_port or int(os.environ.get("WORD_AI_API_PORT", 8000))
    ui_port = args.ui_port or int(os.environ.get("WORD_AI_UI_PORT", 3443))

    base = _get_package_dir()
    addin_dir = base / "word-addin"

    if _port_in_use(api_host, api_port):
        alt = _find_free_port(api_host, api_port + 1)
        print(f"[Word AI] Port {api_port} is already in use, using port {alt} instead.")
        api_port = alt

    api_url = f"http://{api_host}:{api_port}"

    if not addin_dir.exists():
        print(f"[Word AI] ERROR: word-addin directory not found at {addin_dir}")
        print("[Word AI] The add-in UI will not be available.")
    else:
        try:
            cert, key = _find_certs(base)
            start_https_server(addin_dir, cert, key, api_url=api_url, port=ui_port)
        except FileNotFoundError as e:
            print(f"[Word AI] WARNING: {e}")
            print("[Word AI] Add-in UI will not be available. Generate certs first.")

    from app.config import DATA_DIR
    print(f"[Word AI] Data directory: {DATA_DIR}")

    import uvicorn
    print(f"[Word AI] API: {api_url}")
    uvicorn.run(
        "app.main:app",
        host=api_host,
        port=api_port,
        log_level="info",
    )


if __name__ == "__main__":
    start_servers()

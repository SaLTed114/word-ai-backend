from __future__ import annotations

import argparse
import http.server
import ssl
from functools import partial
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--port", type=int, default=3443)
    parser.add_argument("--cert", required=True)
    parser.add_argument("--key", required=True)
    args = parser.parse_args()

    directory = Path(args.directory).resolve()
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("localhost", args.port), handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=args.cert, keyfile=args.key)
    server.socket = context.wrap_socket(server.socket, server_side=True)

    print(f"Serving HTTPS static files from {directory} at https://localhost:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

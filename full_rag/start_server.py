#!/usr/bin/env python3
import os
import socket
import webbrowser

import uvicorn


def find_free_port(host, start_port):
    port = start_port
    while port < start_port + 100:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                port += 1
    raise RuntimeError("No free port found")


def main():
    host = "127.0.0.1"
    start_port = int(os.environ.get("PORT", "8000"))
    port = find_free_port(host, start_port)
    url = f"http://{host}:{port}/"
    if os.environ.get("NO_BROWSER") != "1":
        webbrowser.open(url)
    uvicorn.run("server:app", host=host, port=port)


if __name__ == "__main__":
    main()

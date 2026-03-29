"""TCP bridge for WSL2 -> League Live Client Data API.

Run this ON WINDOWS (not WSL) to forward connections from all interfaces
to the League Live Client API on 127.0.0.1:2999.

Usage (from Windows PowerShell):
    python wsl_bridge.py

Or from WSL:
    powershell.exe -Command "python scripts/wsl_bridge.py"
"""

import socket
import threading
import sys

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 29990
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 2999
BUFFER_SIZE = 65536


def forward(src, dst):
    try:
        while True:
            data = src.recv(BUFFER_SIZE)
            if not data:
                break
            dst.sendall(data)
    except (ConnectionError, OSError):
        pass
    finally:
        src.close()
        dst.close()


def handle_client(client_sock):
    try:
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.connect((TARGET_HOST, TARGET_PORT))

        t1 = threading.Thread(target=forward, args=(client_sock, target_sock), daemon=True)
        t2 = threading.Thread(target=forward, args=(target_sock, client_sock), daemon=True)
        t1.start()
        t2.start()
        t1.join()
    except Exception as e:
        print(f"Connection error: {e}")
        client_sock.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LISTEN_HOST, LISTEN_PORT))
    server.listen(5)
    print(f"WSL Bridge: {LISTEN_HOST}:{LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}")
    print("Waiting for connections...")

    try:
        while True:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
    except KeyboardInterrupt:
        print("\nShutting down")
    finally:
        server.close()


if __name__ == "__main__":
    main()

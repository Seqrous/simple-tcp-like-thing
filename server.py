from __future__ import annotations

from tcp_connection import TCPListener

HOST = 'localhost'
PORT = 80

if __name__ == "__main__":
    tcp_listener = TCPListener(HOST, PORT)
    tcp_listener.listen()
    tcp_listener.accept()

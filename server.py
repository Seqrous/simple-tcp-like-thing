from __future__ import annotations

from tcp_connection import TCPListener

HOST = 'localhost'
PORT = 80

if __name__ == "__main__":
    tcp_listener = TCPListener(HOST, PORT)
    tcp_listener.listen()
    conn = tcp_listener.accept()
    msg = conn.recv(1024)
    print(f"{msg=}")

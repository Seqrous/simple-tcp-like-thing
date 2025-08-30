from __future__ import annotations

from tcp_connection import TCPConnector

SERVER_HOST = 'localhost'
SERVER_PORT = 80

HOST = 'localhost'
PORT = 400

if __name__ == "__main__":
    tcp_connector = TCPConnector(HOST, PORT)
    conn = tcp_connector.connect((SERVER_HOST, SERVER_PORT))
    conn.send(b'Hello World')

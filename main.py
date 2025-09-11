import threading
import time

from tcp_connection.client import Connector
from tcp_connection.server import ConnectionListener
from tcp_connection_v2 import Address

SERVER_HOST = 'localhost'
SERVER_PORT = 80
SERVER_ADDR = Address(host=SERVER_HOST, port=SERVER_PORT)

CLIENT_HOST = 'localhost'
CLIENT_PORT = 400
CLIENT_ADDR = Address(host=CLIENT_HOST, port=CLIENT_PORT)


def run_server():
    s = ConnectionListener(SERVER_ADDR).listen()
    conn = s.accept()


def run_client():
    s = Connector(CLIENT_ADDR)
    conn = s.connect(SERVER_ADDR)


if __name__ == "__main__":
    server_task = threading.Thread(target=run_server)
    client_task = threading.Thread(target=run_client, name="Client")

    server_task.start()
    time.sleep(0.2)
    client_task.start()

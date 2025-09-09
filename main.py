import time

from tcp_connection_v2 import ConnectionContext, Address
import threading

SERVER_HOST = 'localhost'
SERVER_PORT = 80
SERVER_ADDR = Address(host=SERVER_HOST, port=SERVER_PORT)

CLIENT_HOST = 'localhost'
CLIENT_PORT = 400
CLIENT_ADDR = Address(host=CLIENT_HOST, port=CLIENT_PORT)

server = ConnectionContext(SERVER_ADDR)
client = ConnectionContext(CLIENT_ADDR)
server_task = threading.Thread(target=server.listen)
client_task = threading.Thread(target=client.connect, args=(SERVER_ADDR,))

server_task.start()
time.sleep(0.2)
client_task.start()

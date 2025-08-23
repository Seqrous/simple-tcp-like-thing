from __future__ import annotations

import socket
from datagram import Datagram

HOST = 'localhost'
PORT = 4040

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as welcome_socket:
    welcome_socket.bind((HOST, PORT))
    welcome_socket.settimeout(1.0)
    print("Server's up and listening for connections")

    try:
        while True:
            try:
                msg, addr = welcome_socket.recvfrom(1024)
                print(f"Got message from {addr}")
                datagram = Datagram.unpack(msg)
                print(f"{datagram=}")
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("Server's shutting down gracefully")

from __future__ import annotations

import socket
import struct
from random import randbytes

from datagram import Datagram

HOST = 'localhost'
PORT = 80

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

                if datagram.syn:
                    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
                        conn.bind((HOST, 0))
                        _, conn_port = conn.getsockname()
                        ack_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
                        ack_datagram = Datagram(conn_port, datagram.source_port, datagram.seq_number, ack_number, True, True, False, False)
                        welcome_socket.sendto(ack_datagram.pack(), addr)

            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("Server's shutting down gracefully")

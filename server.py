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
                # expect SYN from a client
                msg, addr = welcome_socket.recvfrom(1024)
                print(f"Got message from {addr}")
                datagram = Datagram.unpack(msg)
                print(f"{datagram=}")

                if not datagram.syn:
                    print("Ignoring non-SYN msg")
                    continue

                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
                    conn.bind((HOST, 0))
                    conn.settimeout(5.0)
                    _, conn_port = conn.getsockname()

                    # respond with SYN-ACK, increment client's sequence number
                    seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
                    syn_ack_datagram = Datagram(
                        source_port=conn_port,
                        destination_port=datagram.source_port,
                        seq_number=seq_number,
                        ack_number=datagram.seq_number + 1,
                        syn=True,
                        ack=False,
                        fin=False,
                        rst=False
                    )
                    welcome_socket.sendto(syn_ack_datagram.pack(), addr)
                    seq_number += 1

                    # expect client's ACK
                    ack_msg = conn.recv(1024)
                    ack_datagram = Datagram.unpack(ack_msg)
                    if not ack_datagram.syn and ack_datagram.ack_number == seq_number:
                        print("Handshake successful")
                        continue

                    print("Unacked response from the client")

            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("Server's shutting down gracefully")

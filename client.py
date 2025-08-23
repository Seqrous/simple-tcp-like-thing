from __future__ import annotations
from datagram import Datagram
from random import randbytes
import socket
import struct

SERVER_HOST = 'localhost'
SERVER_PORT = 80

HOST = 'localhost'
PORT = 4000

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as conn:
    conn.settimeout(30.0)
    conn.bind((HOST, PORT))

    # send SYN to the welcome socket
    seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
    syn_datagram = Datagram(
        source_port=PORT,
        destination_port=SERVER_PORT,
        seq_number=seq_number,
        ack_number=0,
        syn=True,
        ack=False,
        fin=False,
        rst=False
    )
    conn.sendto(syn_datagram.pack(), (SERVER_HOST, SERVER_PORT))
    seq_number += 1

    # expect SYN-ACK from the welcome socket
    msg, addr = conn.recvfrom(1024)
    print(f"Got message from {addr}")
    datagram = Datagram.unpack(msg)
    print(f"{datagram=}")
    if datagram.ack_number != seq_number:
        print("Unacked response from the server")
        exit(0)

    # send ACK to the newly assigned connection socket, increment server's sequence number
    ack_datagram = Datagram(
        source_port=PORT,
        destination_port=datagram.source_port,
        seq_number=seq_number,
        ack_number=datagram.seq_number + 1,
        syn=False,
        ack=False,
        fin=False,
        rst=False
    )
    conn.sendto(ack_datagram.pack(), (SERVER_HOST, datagram.source_port))

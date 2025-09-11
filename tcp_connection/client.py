from __future__ import annotations

import struct
from random import randbytes

from datagram import Datagram, TCPFlag
from tcp_connection.utils import seq_increment, Address
import socket


class Connector:
    _peer_addr: Address

    def __init__(self, addr: Address):
        self._addr = addr

    def connect(self, peer_addr: Address) -> TCPConnection:
        print(f"Client: Attempting to establish connection...")
        self._peer_addr = peer_addr
        conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        conn.bind((self._addr.host, self._addr.port))

        seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
        print(f"Client: SEQ number: {seq_number}")
        dgram = Datagram(
            source_port=self._addr.port,
            destination_port=self._peer_addr.port,
            seq_number=seq_number,
            ack_number=0,
            flags=TCPFlag.SYN,
            data=b''
        )
        conn.sendto(dgram.pack(), (self._peer_addr.host, self._peer_addr.port))
        seq_number += seq_increment(dgram.flags, dgram.data)

        print(f"Client: Waiting for SYN-ACK...")
        conn.settimeout(1.0)
        try:
            payload = conn.recv(1024)
        except socket.timeout:
            raise Exception(f"Client timed out waiting for SYN-ACK from the peer")
        conn.settimeout(None)

        dgram = Datagram.unpack(payload)
        print(f"Client: Received {dgram=}")
        if not dgram.has_exact_flags(TCPFlag.SYN | TCPFlag.ACK):
            raise Exception(f"Expected a SYN-ACK response from the peer, got {dgram.flags.name}")

        if dgram.ack_number != seq_number:
            raise Exception(f"UnACKed response from the peer - expected {seq_number}, got {dgram.ack_number}")

        # switch from the welcome socket to the one the server established persistent connection on
        self._peer_addr = Address(self._peer_addr.host, dgram.source_port)
        dgram = Datagram(
            source_port=self._addr.port,
            destination_port=self._peer_addr.port,
            seq_number=seq_number,
            ack_number=dgram.seq_number + seq_increment(dgram.flags, dgram.data),
            flags=TCPFlag.ACK,
            data=b''
        )
        conn.sendto(dgram.pack(), (self._peer_addr.host, self._peer_addr.port))
        seq_number += seq_increment(dgram.flags, dgram.data)

        return TCPConnection()


class TCPConnection:

    def __init__(self):
        print("Client: Connection established")

from __future__ import annotations
import socket
import struct
from random import randbytes

from datagram import Datagram, TCPFlag
from tcp_connection.utils import seq_increment
from tcp_connection_v2 import Address


class ConnectionListener:
    _peer_addr: Address
    _wcm_socket: socket.socket
    _syn_dgram: Datagram

    def __init__(self, addr: Address):
        self._addr = addr

    def listen(self) -> _ConnectionRequestHandler:
        print(f"Server: Listening for connections...")
        self._wcm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._wcm_socket.bind((self._addr.host, self._addr.port))

        self._wcm_socket.settimeout(1.0)  # to allow keyboard interrupts
        try:
            while True:
                try:
                    payload, addr = self._wcm_socket.recvfrom(1024)
                    print(f"Server: Got message from {addr}")
                    dgram = Datagram.unpack(payload)
                    print(f"Server: {dgram=}")

                    if dgram.has_exact_flags(TCPFlag.SYN):
                        self._peer_addr = Address(addr[0], addr[1])
                        self._syn_dgram = dgram
                        # TODO: in the future, it will have to keep listening for other SYN requests
                        break

                    print(f"Server: Ignoring non-SYN msg")

                except socket.timeout:
                    continue

        except KeyboardInterrupt:
            print(f"Server: Shutting down gracefully")
            self._wcm_socket.close()

        return _ConnectionRequestHandler(
            addr=self._addr,
            peer_addr=self._peer_addr,
            wcm_socket=self._wcm_socket,
            syn_dgram=self._syn_dgram
        )


class _ConnectionRequestHandler:
    _conn: socket.socket
    _seq_number: int = 0
    _ack_number: int = 0

    # TODO: introduce a protocol that prevents closing the welcome socket
    def __init__(self, addr: Address, peer_addr: Address, wcm_socket: socket.socket, syn_dgram: Datagram):
        self._addr = addr
        self._peer_addr = peer_addr
        self._wcm_socket = wcm_socket
        self._syn_dgram = syn_dgram

    def accept(self) -> _ServerSideConnection:
        # assign a new socket for persistent connection
        self._conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._conn.bind((self._addr.host, 0))  # random available socket
        _, conn_port = self._conn.getsockname()
        self._addr = Address(self._addr.host, conn_port)

        self._seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
        print(f"Server: SEQ number: {self._seq_number}")
        dgram = Datagram(
            source_port=conn_port,
            destination_port=self._peer_addr.port,
            seq_number=self._seq_number,
            ack_number=self._syn_dgram.seq_number + seq_increment(self._syn_dgram.flags, self._syn_dgram.data),
            flags=TCPFlag.SYN | TCPFlag.ACK,
            data=b''
        )
        self._wcm_socket.sendto(dgram.pack(), (self._peer_addr.host, self._peer_addr.port))
        self._seq_number += seq_increment(dgram.flags, dgram.data)

        # wait for ACK
        self._conn.settimeout(1.0)
        try:
            payload = self._conn.recv(1024)
        except socket.timeout:
            raise Exception(f"Timeout waiting for SYN-ACK from the peer")
        self._conn.settimeout(None)

        dgram = Datagram.unpack(payload)
        if not dgram.has_exact_flags(TCPFlag.ACK):
            raise Exception(f"Expected an ACK response from the peer, got {dgram.flags.name}")

        if dgram.ack_number != self._seq_number:
            raise Exception(f"unACKed response from the peer - expected {self._seq_number}, got {dgram.ack_number}")

        return _ServerSideConnection(
            addr=self._addr,
            peer_addr=self._peer_addr,
            seq_number=self._seq_number,
            ack_number=self._ack_number,
            conn=self._conn
        )


class _ServerSideConnection:

    def __init__(self, addr: Address, peer_addr: Address, seq_number: int, ack_number: int, conn: socket.socket):
        print("Server: Connection established")


from __future__ import annotations

import socket
import struct
from random import randbytes

from datagram import Datagram, TCPFlag


class TCPConnector:

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._socket: socket.socket = None
        self._server_addr: tuple[str, int] = tuple()
        self._seq_number: int = 0
        self._ack_number: int = 0

    def connect(self, addr: tuple[str, int]) -> TCPConnection:
        self._server_addr = addr
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((self.host, self.port))

        try:
            self._request_syn()
            resp = self._await_syn_ack()
            final_ack_datagram = self._ack(resp)
        except Exception:
            self._socket.close()
            raise

        return TCPConnection(
            sock=self._socket,
            addr=(self.host, self.port),
            remote_addr=(self._server_addr[0], resp.source_port),
            seq_number=self._seq_number,
            ack_number=self._ack_number,
            final_ack_datagram=final_ack_datagram
        )

    def _request_syn(self):
        print("SYN request")
        self._seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
        print(f"server's seq number: {self._seq_number}")
        syn_datagram = Datagram(
            source_port=self.port,
            destination_port=self._server_addr[1],
            seq_number=self._seq_number,
            ack_number=self._ack_number,
            flags=TCPFlag.SYN,
            data=b''
        )
        self._socket.sendto(syn_datagram.pack(), self._server_addr)
        self._seq_number += _seq_increment(syn_datagram.flags, syn_datagram.data)

    def _await_syn_ack(self) -> Datagram:
        self._socket.settimeout(1.0)
        print("awaiting SYN-ACK...")

        try:
            msg, addr = self._socket.recvfrom(1024)
        except socket.timeout:
            raise Exception("Timeout waiting for SYN-ACK from the server")

        syn_ack_datagram = Datagram.unpack(msg)
        print(f"{syn_ack_datagram=}")

        self._socket.settimeout(None)  # reset timeout

        if not syn_ack_datagram.has_exact_flags(TCPFlag.SYN | TCPFlag.ACK):
            raise Exception(f"Expected a SYN-ACK response from the server, got {syn_ack_datagram.flags.name}")

        if syn_ack_datagram.ack_number != self._seq_number:
            raise Exception("unACKed response from the server")

        return syn_ack_datagram

    def _ack(self, resp: Datagram) -> Datagram:
        print("ACK connection granted")
        self._ack_number = resp.seq_number + _seq_increment(resp.flags, resp.data)
        ack_datagram = Datagram(
            source_port=self.port,
            destination_port=resp.source_port,
            seq_number=self._seq_number,
            ack_number=self._ack_number,
            flags=TCPFlag.ACK,
            data=b''
        )
        self._socket.sendto(ack_datagram.pack(), (self._server_addr[0], resp.source_port))
        self._seq_number += _seq_increment(ack_datagram.flags, ack_datagram.data) # TODO: ensure this results in +0
        return ack_datagram


class TCPListener:

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self._client_addr: tuple[str, int] = tuple()
        self._seq_number: int = 0
        self._ack_number: int = 0
        self._wcm_socket: socket.socket = None
        self._conn: socket.socket = None
        self._syn_datagram: Datagram = None

    def listen(self) -> None:
        self._wcm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # keep open for other connections
        self._wcm_socket.bind((self.host, self.port))
        self._wcm_socket.settimeout(1.0)

        try:
            while True:
                try:
                    msg, addr = self._wcm_socket.recvfrom(1024)
                    print(f"Got message from {addr}")
                    syn_datagram = Datagram.unpack(msg)
                    print(f"{syn_datagram=}")

                    if syn_datagram.has_exact_flags(TCPFlag.SYN):
                        self._syn_datagram = syn_datagram
                        self._client_addr = addr
                        return

                    print("Ignoring non-SYN msg")

                except socket.timeout:
                    continue

        except KeyboardInterrupt:
            print("Server's shutting down gracefully")
            self._wcm_socket.close()

    def accept(self) -> TCPConnection:
        self._conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._conn.bind((self.host, 0))  # assign random socket
        self._conn.settimeout(1.0)
        _, conn_port = self._conn.getsockname()

        self._seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
        print(f"client's seq number: {self._seq_number}")
        syn_ack_datagram = Datagram(
            source_port=conn_port,
            destination_port=self._client_addr[1],
            seq_number=self._seq_number,
            ack_number=self._syn_datagram.seq_number + _seq_increment(self._syn_datagram.flags, self._syn_datagram.data),
            flags=TCPFlag.SYN | TCPFlag.ACK,
            data=b''
        )
        self._wcm_socket.sendto(syn_ack_datagram.pack(), self._client_addr)
        self._seq_number += _seq_increment(syn_ack_datagram.flags, syn_ack_datagram.data)

        try:
            ack_msg = self._conn.recv(1024)
            self._conn.settimeout(None)  # reset timeout
        except socket.timeout:
            raise Exception("Timeout waiting for ACK from the client")

        ack_datagram = Datagram.unpack(ack_msg)
        print(f"{ack_datagram=}")
        if ack_datagram.has_exact_flags(TCPFlag.ACK) and ack_datagram.ack_number == self._seq_number:
            print("Handshake successful")
            return TCPConnection(
                sock=self._conn,
                addr=(self.host, self.port),
                remote_addr=self._client_addr,
                seq_number=self._seq_number,
                ack_number=ack_datagram.seq_number,
                final_ack_datagram=ack_datagram
            )

        raise Exception("Invalid ACK datagram received during handshake")


class TCPConnection:

    def __init__(
            self,
            sock: socket.socket,
            addr: tuple[str, int],
            remote_addr: tuple[str, int],
            seq_number: int,
            ack_number: int,
            final_ack_datagram: Datagram
    ):
        self._socket = sock
        self._addr = addr
        self._rmt_addr = remote_addr
        self._seq_number = seq_number
        self._ack_number = ack_number
        self._last_datagram = final_ack_datagram

    def send(self, data: bytes):
        datagram = Datagram(
            source_port=self._addr[1],
            destination_port=self._rmt_addr[1],
            seq_number=self._seq_number,
            ack_number=self._ack_number + _seq_increment(self._last_datagram.flags, self._last_datagram.data),
            flags=TCPFlag.ACK,
            data=data
        )
        self._socket.sendto(datagram.pack(), self._rmt_addr)
        self._seq_number += _seq_increment(datagram.flags, datagram.data)

        msg = self._socket.recv(1024)
        ack_datagram = Datagram.unpack(msg)
        if not (ack_datagram.has_exact_flags(TCPFlag.ACK) and ack_datagram.ack_number == self._seq_number):
            raise Exception("unACKed response from the peer")

        self._last_datagram = ack_datagram

    def recv(self, buff_size: int) -> bytes:
        msg = self._socket.recv(buff_size)
        datagram = Datagram.unpack(msg)

        if not (datagram.has_exact_flags(TCPFlag.ACK) and datagram.ack_number == self._seq_number):
            raise Exception("unACKed response from the peer")

        self._last_datagram = datagram
        ack_datagram = Datagram(
            source_port=self._addr[1],
            destination_port=self._rmt_addr[1],
            seq_number=self._seq_number,
            ack_number=self._ack_number + _seq_increment(self._last_datagram.flags, self._last_datagram.data),
            flags=TCPFlag.ACK,
            data=b''
        )
        self._socket.sendto(ack_datagram.pack(), self._rmt_addr)
        self._seq_number += _seq_increment(ack_datagram.flags, ack_datagram.data)

        return self._last_datagram.data

    def set_timeout(self, value: int | None) -> None:
        self._socket.settimeout(value)


def _seq_increment(flags: TCPFlag, data: bytes) -> int:
    ctrl_flags = TCPFlag.SYN | TCPFlag.FIN
    if (flags & ctrl_flags) and len(data) == 0:
        return 1

    return len(data)

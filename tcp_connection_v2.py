from __future__ import annotations

import abc
import socket
import struct
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from random import randbytes

from datagram import Datagram, TCPFlag


@dataclass
class Address:
    host: str
    port: int


class TCPStateName(Enum):
    CLOSED = 0
    LISTEN = 1
    SYN_SENT = 2
    SYN_RECEIVED = 3
    ESTABLISHED = 4


class StateFactory:

    def __init__(self):
        self.mapping: dict[TCPStateName, Callable[[], State]] = {
            TCPStateName.CLOSED: ClosedState,
            TCPStateName.LISTEN: ListenState,
            TCPStateName.SYN_SENT: SynSentState,
            TCPStateName.SYN_RECEIVED: SynReceivedState,
            TCPStateName.ESTABLISHED: EstablishedState
        }

    def create(self, name: TCPStateName):
        init = self.mapping.get(name)
        if init is None:
            raise Exception(f"No class configured for {name=}")

        return init()


class ConnectionContext:
    closed: bool = True
    conn_socket: socket.socket
    wcm_socket: socket.socket
    addr: Address
    rmt_addr: Address
    seq_number: int = 0
    ack_number: int = 0

    syn_dgram: Datagram # part of the listener (used in listen and SYN-ACK)

    _state: State
    _state_name: TCPStateName
    _state_factory: StateFactory

    def __init__(self, addr: Address):
        self.addr = addr

        self._state_factory = StateFactory()
        self._state = None
        self._state_name = None

    def set_state(self, new_state_name: TCPStateName):
        # for debugging
        if self._state_name is None:
            print(f"No current state, setting {new_state_name.name}")
        else:
            print(f"Changing state from {self._state_name.name} to {new_state_name.name}")

        self._state = self._state_factory.create(name=new_state_name)
        self._state.set_context(self)
        self._state_name = new_state_name

    def connect(self, rmt_addr: Address):
        print("[Client]: Attempting to establish connection...")
        self.rmt_addr = rmt_addr
        self.conn_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.conn_socket.bind((self.addr.host, self.addr.port))
        self.set_state(new_state_name=TCPStateName.CLOSED)
        self.handle()

    def listen(self):
        print("[Server]: Listening for connections...")
        self.wcm_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.wcm_socket.bind((self.addr.host, self.addr.port))
        self.set_state(new_state_name=TCPStateName.LISTEN)
        self.handle()

    def handle(self):
        self._state.handle()


class State(abc.ABC):
    _ctx: ConnectionContext

    def set_context(self, ctx: ConnectionContext):
        self._ctx = ctx

    def handle(self) -> None:
        raise NotImplementedError


class ClosedState(State):

    def handle(self) -> None:
        # TODO: might want to introduce another method/protocol for this
        if self._ctx.closed:
            self._ctx.seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
            print(f"[Client]: Client's SEQ number: {self._ctx.seq_number}")
            dgram = Datagram(
                source_port=self._ctx.addr.port,
                destination_port=self._ctx.rmt_addr.port,
                seq_number=self._ctx.seq_number,
                ack_number=self._ctx.ack_number,
                flags=TCPFlag.SYN,
                data=b''
            )
            self._ctx.conn_socket.sendto(dgram.pack(), (self._ctx.rmt_addr.host, self._ctx.rmt_addr.port))
            self._ctx.seq_number += _seq_increment(dgram.flags, dgram.data)
            self._ctx.set_state(TCPStateName.SYN_SENT)
            self._ctx.handle()

        # TODO: otherwise, request closure

class ListenState(State):

    def handle(self) -> None:
        # TODO: introduce an interface with .listen()
        # TODO: for capturing SYNs
        # TODO: return interface with .accept() that will use that SYN dgram
        self._ctx.wcm_socket.settimeout(1.0)  # otherwise it will block and swallow keyboard interrupts
        try:
            while True:
                try:
                    payload, addr = self._ctx.wcm_socket.recvfrom(1024)
                    print(f"[Server]: Got message from {addr}")
                    dgram = Datagram.unpack(payload)
                    print(f"[Server]: {dgram=}")

                    if dgram.has_exact_flags(TCPFlag.SYN):
                        self._ctx.rmt_addr = Address(addr[0], addr[1])
                        self._ctx.syn_dgram = dgram
                        # TODO: at some point, spawn another thread to keep listening for other SYN requests
                        break

                    print("[Server]: Ignoring non-SYN msg")

                except socket.timeout:
                    continue

            self._ctx.set_state(TCPStateName.SYN_RECEIVED)
            self._ctx.handle()

        except KeyboardInterrupt:
            print("[Server]: Shutting down gracefully")
            self._ctx.wcm_socket.close()

class SynSentState(State):

    def handle(self) -> None:
        print("[Client]: awaiting SYN-ACK...")
        self._ctx.conn_socket.settimeout(1.0)
        try:
            payload = self._ctx.conn_socket.recv(1024)
        except socket.timeout:
            raise Exception("[Client]: Timeout waiting for SYN-ACK from the peer")
        self._ctx.conn_socket.settimeout(None)

        dgram = Datagram.unpack(payload)
        print(f"[Client]: {dgram=}")
        if not dgram.has_exact_flags(TCPFlag.SYN | TCPFlag.ACK):
            raise Exception(f"[Client]: Expected a SYN-ACK response from the peer, got {dgram.flags.name}")

        if dgram.ack_number != self._ctx.seq_number:
            raise Exception(f"[Client]: unACKed response from the peer - expected {self._ctx.seq_number}, got {dgram.ack_number}")

        self._ctx.ack_number = dgram.seq_number

        # switch from the welcome socket to the one the server established persistent connection on
        self._ctx.rmt_addr = Address(self._ctx.rmt_addr.host, dgram.source_port)
        resp_dgram = Datagram(
            source_port=self._ctx.addr.port,
            destination_port=self._ctx.rmt_addr.port,
            seq_number=self._ctx.seq_number,
            ack_number=self._ctx.ack_number + _seq_increment(dgram.flags, dgram.data),
            flags=TCPFlag.ACK,
            data=b''
        )
        self._ctx.conn_socket.sendto(resp_dgram.pack(), (self._ctx.rmt_addr.host, self._ctx.rmt_addr.port))
        self._ctx.seq_number += _seq_increment(resp_dgram.flags, resp_dgram.data)
        self._ctx.set_state(TCPStateName.ESTABLISHED)
        self._ctx.handle()


class SynReceivedState(State):

    def handle(self) -> None:
        # assign a new socket for persistent connection
        self._ctx.conn_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._ctx.conn_socket.bind((self._ctx.addr.host, 0))  # random available socket
        _, conn_port = self._ctx.conn_socket.getsockname()
        self._ctx.addr = Address(self._ctx.addr.host, conn_port)

        self._ctx.seq_number = int(struct.unpack('I', randbytes(4))[0])  # 32bit int
        print(f"[Server]: Server's SEQ number: {self._ctx.seq_number}")
        dgram = Datagram(
            source_port=conn_port,
            destination_port=self._ctx.rmt_addr.port,
            seq_number=self._ctx.seq_number,
            ack_number=self._ctx.syn_dgram.seq_number + _seq_increment(self._ctx.syn_dgram.flags, self._ctx.syn_dgram.data),
            flags=TCPFlag.SYN | TCPFlag.ACK,
            data=b''
        )
        self._ctx.wcm_socket.sendto(dgram.pack(), (self._ctx.rmt_addr.host, self._ctx.rmt_addr.port))
        self._ctx.seq_number += _seq_increment(dgram.flags, dgram.data)

        # wait for ACK
        self._ctx.conn_socket.settimeout(1.0)
        try:
            payload = self._ctx.conn_socket.recv(1024)
        except socket.timeout:
            raise Exception("[Server]: Timeout waiting for SYN-ACK from the peer")
        self._ctx.conn_socket.settimeout(None)

        dgram = Datagram.unpack(payload)
        if not dgram.has_exact_flags(TCPFlag.ACK):
            raise Exception(f"[Server]: Expected an ACK response from the peer, got {dgram.flags.name}")

        if dgram.ack_number != self._ctx.seq_number:
            raise Exception(f"[Server]: unACKed response from the peer - expected {self._ctx.seq_number}, got {dgram.ack_number}")

        self._ctx.set_state(TCPStateName.ESTABLISHED)
        self._ctx.handle()


class EstablishedState(State):

    def handle(self) -> None:
        print("Connection established :)")


def _seq_increment(flags: TCPFlag, data: bytes) -> int:
    ctrl_flags = TCPFlag.SYN | TCPFlag.FIN
    if (flags & ctrl_flags) and len(data) == 0:
        return 1

    return len(data)

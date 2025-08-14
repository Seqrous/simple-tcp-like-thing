import socket
import struct
from dataclasses import dataclass

SERVER_HOST = 'localhost'
SERVER_PORT = 4040

HOST = 'localhost'
PORT = 4080


@dataclass
class Datagram:
    source_port: int
    destination_port: int

    FORMAT = 'hh'

    def pack(self) -> bytes:
        return struct.pack(self.FORMAT, self.source_port, self.destination_port)

    @classmethod
    def unpack(cls, data: bytes) -> "Datagram":
        unpacked = struct.unpack(cls.FORMAT, data)
        return cls(source_port=unpacked[0], destination_port=unpacked[1])


with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind((HOST, PORT))
    test_datagram = Datagram(PORT, SERVER_PORT)
    s.sendto(test_datagram.pack(), (SERVER_HOST, SERVER_PORT))

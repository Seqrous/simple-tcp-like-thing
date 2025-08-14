import socket
import struct
from dataclasses import dataclass

HOST = 'localhost'
PORT = 4040


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

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntFlag


class TCPFlag(IntFlag):
    NONE = 0
    SYN = 1 << 0
    ACK = 1 << 1
    FIN = 1 << 2
    RST = 1 << 3


@dataclass(frozen=True)
class Datagram:
    source_port: int
    destination_port: int
    seq_number: int
    ack_number: int
    flags: TCPFlag
    data: bytes

    FORMAT = 'HHIIB 255s'

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.source_port,
            self.destination_port,
            self.seq_number,
            self.ack_number,
            self.flags,
            self.data
        )

    @classmethod
    def unpack(cls, data: bytes) -> Datagram:
        unpacked = struct.unpack(cls.FORMAT, data)
        return cls(
            source_port=unpacked[0],
            destination_port=unpacked[1],
            seq_number=unpacked[2],
            ack_number=unpacked[3],
            flags=TCPFlag(unpacked[4]),
            data=unpacked[5]
        )

    def has_exact_flags(self, flags: TCPFlag) -> bool:
        return self.flags == flags

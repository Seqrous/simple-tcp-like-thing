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

    HEADER_FORMAT = 'HHIIB'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

    def pack(self) -> bytes:
        header = struct.pack(
            self.HEADER_FORMAT,
        self.source_port,
            self.destination_port,
            self.seq_number,
            self.ack_number,
            self.flags
        )
        return header + self.data

    @classmethod
    def unpack(cls, payload: bytes) -> Datagram:
        header_bytes = payload[:cls.HEADER_SIZE]
        data_bytes = payload[cls.HEADER_SIZE:]

        headers = struct.unpack(cls.HEADER_FORMAT, header_bytes)
        return cls(
            source_port=headers[0],
            destination_port=headers[1],
            seq_number=headers[2],
            ack_number=headers[3],
            flags=TCPFlag(headers[4]),
            data=data_bytes
        )

    def has_exact_flags(self, flags: TCPFlag) -> bool:
        return self.flags == flags

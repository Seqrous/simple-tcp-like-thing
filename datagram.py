from __future__ import annotations
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class Datagram:
    source_port: int
    destination_port: int
    seq_number: int
    ack_number: int
    syn: bool
    ack: bool
    fin: bool
    rst: bool

    FORMAT = 'HHIIB'

    def pack(self) -> bytes:
        flags = (
                (self.syn << 0) |
                (self.ack << 1) |
                (self.fin << 2) |
                (self.rst << 3)
        )
        return struct.pack(
            self.FORMAT,
            self.source_port,
            self.destination_port,
            self.seq_number,
            self.ack_number,
            flags
        )

    @classmethod
    def unpack(cls, data: bytes) -> Datagram:
        unpacked = struct.unpack(cls.FORMAT, data)
        flags = unpacked[4]
        return cls(
            source_port=unpacked[0],
            destination_port=unpacked[1],
            seq_number=unpacked[2],
            ack_number=unpacked[3],
            syn=_get_bit(flags, 0),
            ack=_get_bit(flags, 1),
            fin=_get_bit(flags, 2),
            rst=_get_bit(flags, 3)
        )


def _get_bit(value: int, n: int) -> bool:
    return (value & (1 << n)) != 0

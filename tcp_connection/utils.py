from dataclasses import dataclass

from datagram import TCPFlag


@dataclass
class Address:
    host: str
    port: int


def seq_increment(flags: TCPFlag, data: bytes) -> int:
    ctrl_flags = TCPFlag.SYN | TCPFlag.FIN
    if (flags & ctrl_flags) and len(data) == 0:
        return 1

    return len(data)

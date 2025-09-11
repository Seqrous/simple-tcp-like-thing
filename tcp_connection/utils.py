from datagram import TCPFlag


def seq_increment(flags: TCPFlag, data: bytes) -> int:
    ctrl_flags = TCPFlag.SYN | TCPFlag.FIN
    if (flags & ctrl_flags) and len(data) == 0:
        return 1

    return len(data)

import os
import re

HUMAN_SIZE = re.compile("(\d+\.?\d*G)|(\d+\.?\d*M)|(\d+\.?\d*K)|(\d+\.?\d*)")

class InvalidFormat(Exception):
    pass

def human_size_to_bytes(human_size):
    """
    Converts a size specified in a human friendly way (for example 1G, 10M,
    30K) into bytes.
    """
    gb, mb, kb, b = HUMAN_SIZE.match(human_size).groups()
    if gb is not None:
        b = float(gb[:-1]) * (1024 ** 3)
    elif mb is not None:
        b = float(mb[:-1]) * (1024 ** 2)
    elif kb is not None:
        b = float(kb[:-1]) * 1024
    elif b is not None:
        b = float(b)
    else:
        raise InvalidFormat
    return b


def directory_usage(path):
    total_usage = 0
    for root, dirs, filenames in os.walk(path):
        for filename in filenames:
            fp = os.path.join(root, filename)
            total_usage += os.path.getsize(fp)
    return total_usage

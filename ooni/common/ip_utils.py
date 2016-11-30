from ipaddr import IPv4Address, IPv6Address
from ipaddr import AddressValueError


def is_public_ipv4_address(address):
    return not is_private_ipv4_address(address)


def is_private_ipv4_address(address):
    try:
        ip_address = IPv4Address(address)
        return any(
            [ip_address.is_private, ip_address.is_loopback]
        )
    except AddressValueError:
        return False


def is_private_address(address, only_loopback=False):
    """
    Checks to see if an IP address is in private IP space and if the
    hostname is either localhost or *.local.

    :param address: an IP address of a hostname
    :param only_loopback: will only check if the IP address is either
        127.0.0.1/8 or ::1 in ipv6
    :return: True if the IP address or host is in private space
    """
    try:
        ip_address = IPv4Address(address)
    except AddressValueError:
        try:
            ip_address = IPv6Address(address)
        except AddressValueError:
            if address == "localhost":
                return True
            elif address.endswith(".local"):
                return True
            return False

    candidates = [ip_address.is_loopback]
    if not only_loopback:
        candidates.append(ip_address.is_private)
    return any(candidates)

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

def is_private_address(address):
    try:
        ip_address = IPv4Address(address)
    except AddressValueError:
        try:
            ip_address = IPv6Address(address)
        except AddressValueError:
            return False

    return any(
        [ip_address.is_private, ip_address.is_loopback]
    )

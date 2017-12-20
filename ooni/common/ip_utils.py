from ipaddr import IPv4Address, IPv6Address, IPv4Network
from ipaddr import AddressValueError

def is_global(ip_address):
	return (ip_address not in IPv4Network('100.64.0.0/10') and
		not ip_address.is_private)

def in_private_ip_space(address):
    ip_address = IPv4Address(address)
    return any(
        [not is_global(ip_address), ip_address.is_loopback]
    )

def is_public_ipv4_address(address):
    try:
        return not in_private_ip_space(address)
    except AddressValueError:
        return False

def is_private_ipv4_address(address):
    try:
        return in_private_ip_space(address)
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
        candidates.append(not is_global(ip_address))
    return any(candidates)

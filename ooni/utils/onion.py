import string
import subprocess
from distutils.spawn import find_executable
from distutils.version import LooseVersion

from txtorcon.util import find_tor_binary as tx_find_tor_binary

from ooni.settings import config


class TorVersion(LooseVersion):
    pass


class OBFSProxyVersion(LooseVersion):
    pass


def find_tor_binary():
    if config.advanced.tor_binary:
        return config.advanced.tor_binary
    return tx_find_tor_binary()


def executable_version(binary, strip=lambda x: x):
    if not binary:
        return None
    try:
        proc = subprocess.Popen((binary, '--version'),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        pass
    else:
        stdout, _ = proc.communicate()
        if proc.poll() == 0 and stdout != '':
            version = stdout.strip()
            return LooseVersion(strip(version))
    return None


def tor_version():
    version = executable_version(find_tor_binary(),
                                 lambda x: x.split(' ')[2])
    return TorVersion(str(version))


def obfsproxy_version():
    version = executable_version(find_executable('obfsproxy'))
    return OBFSProxyVersion(str(version))


def transport_name(address):
    """
    If the address of the bridge starts with a valid c identifier then
    we consider it to be a bridge.
    Returns:
        The transport_name if it's a transport.
        None if it's not a obfsproxy bridge.
    """
    transport_name = address.split(' ')[0]
    transport_name_chars = string.ascii_letters + string.digits
    if all(c in transport_name_chars for c in transport_name):
        return transport_name
    else:
        return None


tor_details = {
    'binary': find_tor_binary(),
    'version': tor_version()
}

obfsproxy_details = {
    'binary': find_executable('obfsproxy'),
    'version': obfsproxy_version()
}

import string
import subprocess
from distutils.version import LooseVersion

from txtorcon.util import find_tor_binary

class TorVersion(LooseVersion):
    pass

def tor_version():
    tor_binary = find_tor_binary()
    if not tor_binary:
        return None
    try:
        proc = subprocess.Popen((tor_binary, '--version'),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError:
        pass
    else:
        stdout, _ = proc.communicate()
        if proc.poll() == 0 and stdout != '':
            return TorVersion(stdout.strip().split(' ')[2])
    return None

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

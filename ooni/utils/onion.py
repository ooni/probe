import re
import string
import subprocess
from distutils.spawn import find_executable
from distutils.version import LooseVersion

from txtorcon.util import find_tor_binary as tx_find_tor_binary

from ooni.settings import config

ONION_ADDRESS_REGEXP = re.compile("^((httpo|http|https)://)?"
                                  "[a-z0-9]{16}\.onion")

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


def is_onion_address(address):
    return ONION_ADDRESS_REGEXP.match(address) != None



tor_details = {
    'binary': find_tor_binary(),
    'version': tor_version()
}

obfsproxy_details = {
    'binary': find_executable('obfsproxy'),
    'version': obfsproxy_version()
}

transport_bin_name = { 'fte': 'fteproxy',
                       'scramblesuit': 'obfsproxy',
                       'obfs2': 'obfsproxy',
                       'obfs3': 'obfsproxy',
                       'obfs4': 'obfs4proxy' }

_pyobfsproxy_line = lambda transport, bin_loc, log_file: \
    "%s exec %s --log-min-severity info --log-file %s managed" % \
    (transport, bin_loc, log_file)

_transport_line_templates = {
    'fte': lambda bin_loc, log_file : \
        "fte exec %s --managed" % bin_loc,

    'scramblesuit': lambda bin_loc, log_file: \
        _pyobfsproxy_line('scramblesuit', bin_loc, log_file),

    'obfs2': lambda bin_loc, log_file: \
        _pyobfsproxy_line('obfs2', bin_loc, log_file),

    'obfs3': lambda bin_loc, log_file: \
        _pyobfsproxy_line('obfs3', bin_loc, log_file),

    'obfs4': lambda bin_loc, log_file: \
        "obfs4 exec %s --enableLogging=true --logLevel=INFO" % bin_loc }

class UnrecognizedTransport(Exception):
    pass
class UninstalledTransport(Exception):
    pass
class OutdatedObfsproxy(Exception):
    pass
class OutdatedTor(Exception):
    pass

def bridge_line(transport, log_file):
    bin_name = transport_bin_name.get(transport)
    if not bin_name:
        raise UnrecognizedTransport

    bin_loc = find_executable(bin_name)
    if not bin_loc:
        raise UninstalledTransport

    if OBFSProxyVersion('0.2') > obfsproxy_details['version']:
        raise OutdatedObfsproxy

    if (transport == 'scramblesuit' or \
            bin_name == 'obfs4proxy') and \
            TorVersion('0.2.5.1') > tor_details['version']:
        raise OutdatedTor

    if TorVersion('0.2.4.1') > tor_details['version']:
        raise OutdatedTor

    return _transport_line_templates[transport](bin_loc, log_file)

import os
import re
import pwd
import fcntl
import errno
import string
import StringIO
import subprocess
from distutils.spawn import find_executable
from distutils.version import LooseVersion

from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint

from txtorcon import TorConfig, TorState, launch_tor, build_tor_connection
from txtorcon.util import find_tor_binary as tx_find_tor_binary

from ooni.utils import mkdir_p
from ooni.utils.net import randomFreePort
from ooni import constants
from ooni import errors
from ooni.utils import log
from ooni.settings import config

ONION_ADDRESS_REGEXP = re.compile("^((httpo|http|https)://)?"
                                  "[a-z0-9]{16}\.onion")

TBB_PT_PATHS = ("/Applications/TorBrowser.app/Contents/MacOS/Tor"
                "/PluggableTransports/",)

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
    return None


def is_onion_address(address):
    return ONION_ADDRESS_REGEXP.match(address) != None


def find_pt_executable(name):
    bin_loc = find_executable(name)
    if bin_loc:
        return bin_loc
    for path in TBB_PT_PATHS:
        bin_loc = os.path.join(path, name)
        if os.path.isfile(bin_loc):
            return bin_loc
    return None

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
        "obfs4 exec %s --enableLogging=true --logLevel=INFO" % bin_loc,

}

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

pt_config = {
    'meek': [
        {
            'executable': 'obfs4proxy',
            'minimum_version': '0.0.6',
            'version_parse': lambda x: x.split('-')[1],
            'client_transport_line': 'meek exec {bin_loc}'
        },
        {
            'executable': 'meek-client',
            'minimum_version': None,
            'client_transport_line': 'meek exec {bin_loc}'
        }
    ],

    'obfs4': [
        {
            'executable': 'obfs4proxy',
            'minimum_version': None,
            'client_transport_line': 'obfs4 exec {bin_loc}'
        }
    ]

}

def get_client_transport(transport):
    """

    :param transport:
    :return: client_transport_line
    """

    try:
        pts = pt_config[transport]
    except KeyError:
        raise UnrecognizedTransport

    for pt in pts:
        bin_loc = find_pt_executable(pt['executable'])
        if bin_loc is None:
            continue
        if pt['minimum_version'] is not None:
            pt_version = executable_version(bin_loc, pt['version_parse'])
            if (pt_version is None or
                        pt_version < LooseVersion(pt['minimum_version'])):
                continue
        return pt['client_transport_line'].format(bin_loc=bin_loc)

    raise UninstalledTransport

def is_tor_data_dir_usable(tor_data_dir):
    """
    Checks if the Tor data dir specified is usable. This means that
     it is not being locked and we have permissions to write to it.
    """
    if not os.path.exists(tor_data_dir):
        return True

    try:
        fcntl.flock(open(os.path.join(tor_data_dir, 'lock'), 'w'),
                    fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except (IOError, OSError) as err:
        if err.errno == errno.EACCES:
            # Permission error
            return False
        elif err.errno == errno.EAGAIN:
            # File locked
            return False

def get_tor_config():
    tor_config = TorConfig()
    if config.tor.control_port is None:
        config.tor.control_port = int(randomFreePort())
    if config.tor.socks_port is None:
        config.tor.socks_port = int(randomFreePort())

    tor_config.ControlPort = config.tor.control_port
    tor_config.SocksPort = config.tor.socks_port

    if config.tor.data_dir:
        data_dir = os.path.expanduser(config.tor.data_dir)
        # We only use the Tor data dir specified in the config file if
        # 1. It is not locked (i.e. another process is using it)
        # 2. We have write permissions to it
        data_dir_usable = is_tor_data_dir_usable(data_dir)
        try:
            mkdir_p(data_dir)
        except OSError as ose:
            if ose.errno == errno.EACCESS:
                data_dir_usable = False
            else:
                raise
        if data_dir_usable:
            tor_config.DataDirectory = data_dir

    if config.tor.bridges:
        tor_config.UseBridges = 1
        if config.advanced.obfsproxy_binary:
            tor_config.ClientTransportPlugin = (
                'obfs2,obfs3 exec %s managed' %
                config.advanced.obfsproxy_binary
            )
        bridges = []
        with open(config.tor.bridges) as f:
            for bridge in f:
                if 'obfs' in bridge:
                    if config.advanced.obfsproxy_binary:
                        bridges.append(bridge.strip())
                else:
                    bridges.append(bridge.strip())
        tor_config.Bridge = bridges

    if config.tor.torrc:
        for i in config.tor.torrc.keys():
            setattr(tor_config, i, config.tor.torrc[i])

    if os.geteuid() == 0:
        tor_config.User = pwd.getpwuid(os.geteuid()).pw_name

    tor_config.save()
    log.debug("Setting control port as %s" % tor_config.ControlPort)
    log.debug("Setting SOCKS port as %s" % tor_config.SocksPort)
    return tor_config

class TorLauncherWithRetries(object):
    def __init__(self, tor_config, timeout=config.tor.timeout):
        self.retry_with = ["obfs4", "meek"]
        self.started = defer.Deferred()
        self.tor_output = StringIO.StringIO()
        self.tor_config = tor_config
        if timeout is None:
            # XXX we will want to move setting the default inside of the
            # config object.
            timeout = 200
        self.timeout = timeout

    def _reset_tor_config(self):
        """
        This is used to reset the Tor configuration to before launch_tor
        modified it. This is in particular used to force the regeneration of the
        DataDirectory.
        """
        new_tor_config = TorConfig()
        for key in self.tor_config:
            if config.tor.data_dir is None and key == "DataDirectory":
                continue
            setattr(new_tor_config, key, getattr(self.tor_config, key))
        self.tor_config = new_tor_config

    def _progress_updates(self, prog, tag, summary):
        log.msg("%d%%: %s" % (prog, summary))

    @defer.inlineCallbacks
    def _state_complete(self, state):
        config.tor_state = state
        log.debug("We now have the following circuits: ")
        for circuit in state.circuits.values():
            log.debug(" * %s" % circuit)

        socks_port = yield state.protocol.get_conf("SocksPort")
        control_port = yield state.protocol.get_conf("ControlPort")

        config.tor.socks_port = int(socks_port.values()[0])
        config.tor.control_port = int(control_port.values()[0])
        self.started.callback(state)

    def _setup_failed(self, failure):
        self.tor_output.seek(0)
        map(log.debug, self.tor_output.readlines())
        self.tor_output.seek(0)

        if len(self.retry_with) == 0:
            self.started.errback(errors.UnableToStartTor())
            return

        while len(self.retry_with) > 0:
            self._reset_tor_config()
            self.tor_config.UseBridges = 1
            transport = self.retry_with.pop(0)
            log.msg("Failed to start Tor. Retrying with {0}".format(transport))

            try:
                bridge_lines = getattr(constants,
                                       '{0}_BRIDGES'.format(transport).upper())
            except AttributeError:
                continue

            try:
                self.tor_config.ClientTransportPlugin = get_client_transport(transport)
            except UninstalledTransport:
                log.err("Pluggable transport {0} is not installed".format(
                    transport))
                continue
            except UnrecognizedTransport:
                log.err("Unrecognized transport type")
                continue

            self.tor_config.Bridge = bridge_lines
            self.launch()
            break

    def _setup_complete(self, proto):
        """
        Called when we read from stdout that Tor has reached 100%.
        """
        log.debug("Building a TorState")
        config.tor.protocol = proto
        state = TorState(proto.tor_protocol)
        state.post_bootstrap.addCallbacks(self._state_complete,
                                          self._setup_failed)

    def _launch_tor(self):
        return launch_tor(self.tor_config, reactor,
                          tor_binary=config.advanced.tor_binary,
                          progress_updates=self._progress_updates,
                          stdout=self.tor_output,
                          timeout=self.timeout,
                          stderr=self.tor_output)

    def launch(self):
        self._launched = self._launch_tor()
        self._launched.addCallbacks(self._setup_complete, self._setup_failed)
        return self.started


def start_tor(tor_config):
    tor_launcher = TorLauncherWithRetries(tor_config)
    return tor_launcher.launch()


@defer.inlineCallbacks
def connect_to_control_port():
    connection = TCP4ClientEndpoint(reactor, '127.0.0.1',
                                    config.tor.control_port)
    config.tor_state = yield build_tor_connection(connection)

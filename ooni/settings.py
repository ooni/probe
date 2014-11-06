import os
import sys
import yaml
import getpass

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from os.path import abspath, expanduser

from ooni.utils.net import ConnectAndCloseProtocol, connectProtocol
from ooni import geoip
from ooni.utils import Storage, log
from ooni import errors


class OConfig(object):
    _custom_home = None

    def __init__(self):
        self.current_user = getpass.getuser()
        self.global_options = {}
        self.reports = Storage()
        self.scapyFactory = None
        self.tor_state = None
        # This is used to store the probes IP address obtained via Tor
        self.probe_ip = geoip.ProbeIP()
        self.logging = True
        self.basic = Storage()
        self.advanced = Storage()
        self.tor = Storage()
        self.privacy = Storage()
        self.set_paths()

    @property
    def data_directory(self):
        data_directory = abspath(os.path.join(__file__, '..', '..', 'data'))

        if os.getenv("OONI_DATA_DIR"):
            data_directory = os.getenv("OONI_DATA_DIR")
        elif self.global_options.get('datadir'):
            data_directory = abspath(expanduser(self.global_options['datadir']))
        elif self.advanced.get('data_dir'):
            data_directory = self.advanced['data_dir']
        elif hasattr(sys, 'real_prefix'):
            data_directory = os.path.abspath(os.path.join(sys.prefix, 'share', 'ooni'))
        elif not os.path.exists(data_directory):
            data_directory = '/var/lib/ooni/'

        return data_directory

    def set_paths(self, ooni_home=None):
        if ooni_home:
            self._custom_home = ooni_home

        self.nettest_directory = abspath(os.path.join(__file__, '..', 'nettests'))

        self.ooni_home = os.path.join(expanduser('~'+self.current_user), '.ooni')
        if self._custom_home:
            self.ooni_home = self._custom_home
        self.inputs_directory = os.path.join(self.ooni_home, 'inputs')
        self.decks_directory = os.path.join(self.ooni_home, 'decks')
        self.reports_directory = os.path.join(self.ooni_home, 'reports')
        self.report_log_file = os.path.join(self.ooni_home, 'reporting.yml')
        self.resources_directory = os.path.join(self.data_directory, "resources")

        if self.global_options.get('configfile'):
            config_file = self.global_options['configfile']
            self.config_file = expanduser(config_file)
        else:
            self.config_file = os.path.join(self.ooni_home, 'ooniprobe.conf')

        if 'logfile' in self.basic:
            self.basic.logfile = expanduser(self.basic.logfile.replace('~','~'+self.current_user))

        if not os.path.exists(self.data_directory):
            log.err("Data directory %s does not exists" % self.data_directory)
            log.err("Edit data_dir inside of %s" % self.config_file)


    def initialize_ooni_home(self, ooni_home=None):
        if ooni_home:
            self.set_paths(ooni_home)

        if not os.path.isdir(self.ooni_home):
            print "Ooni home directory does not exist."
            print "Creating it in '%s'." % self.ooni_home
            os.mkdir(self.ooni_home)
            os.mkdir(self.inputs_directory)
            os.mkdir(self.decks_directory)
        if not os.path.isdir(self.reports_directory):
            os.mkdir(self.reports_directory)

    def _create_config_file(self):
        target_config_file = self.config_file
        print "Creating it for you in '%s'." % target_config_file
        sample_config_file = os.path.join(self.data_directory,
                                          'ooniprobe.conf.sample')

        with open(sample_config_file) as f:
            with open(target_config_file, 'w+') as w:
                for line in f:
                    if line.startswith('    data_dir: '):
                        w.write('    data_dir: %s\n' % self.data_directory)
                    elif line.startswith('    logfile: '):
                        w.write('    logfile: %s\n' % os.path.join(self.ooni_home, 'ooniprobe.log'))
                    else:
                        w.write(line)

    def read_config_file(self, check_incoherences=False):
        if not os.path.isfile(self.config_file):
            print "Configuration file does not exist."
            self._create_config_file()
            self.read_config_file()

        with open(self.config_file) as f:
            config_file_contents = '\n'.join(f.readlines())
            configuration = yaml.safe_load(config_file_contents)

        for setting in configuration.keys():
            if setting in dir(self) and configuration[setting] is not None:
                for k, v in configuration[setting].items():
                    getattr(self, setting)[k] = v

        self.set_paths()
        if check_incoherences:
            self.check_incoherences(configuration)

    def check_incoherences(self, configuration):
        incoherent = []

        if configuration['advanced']['interface'] != 'auto':
            from scapy.all import get_if_list
            if configuration['advanced']['interface'] not in get_if_list():
                incoherent.append('advanced:interface')

        self.log_incoherences(incoherent)

    def log_incoherences(self, incoherences):
        if len(incoherences) > 0:
            if len(incoherences) > 1:
                incoherent_pretty = ", ".join(incoherences[:-1]) + ' and ' + incoherences[-1]
            else:
                incoherent_pretty = incoherences[0]
            log.err("You must set properly %s in %s." % (incoherent_pretty, self.config_file))
            raise errors.ConfigFileIncoherent

    @defer.inlineCallbacks
    def check_tor(self):
        """
        Called only when we must start tor by director.start
        """
        incoherent = []
        if not self.advanced.start_tor:
            if self.tor.socks_port is None:
                incoherent.append('tor:socks_port')
            else:
                socks_port_ep = TCP4ClientEndpoint(reactor,
                                                   "localhost",
                                                   self.tor.socks_port)
                try:
                    yield connectProtocol(socks_port_ep, ConnectAndCloseProtocol())
                except Exception:
                    incoherent.append('tor:socks_port')

            if self.tor.control_port is not None:
                control_port_ep = TCP4ClientEndpoint(reactor,
                                                     "localhost",
                                                     self.tor.control_port)
                try:
                    yield connectProtocol(control_port_ep, ConnectAndCloseProtocol())
                except Exception:
                    incoherent.append('tor:control_port')

            self.log_incoherences(incoherent)

config = OConfig()
if not os.path.isfile(config.config_file) \
       and os.path.isfile('/etc/ooni/ooniprobe.conf'):
    config.global_options['configfile'] = '/etc/ooniprobe.conf'
    config.set_paths(ooni_home=config.advanced.data_dir)

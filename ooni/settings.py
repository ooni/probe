import os
import yaml
import getpass
from ConfigParser import SafeConfigParser

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from os.path import abspath, expanduser

from ooni.utils.net import ConnectAndCloseProtocol, connectProtocol
from ooni import geoip
from ooni.utils import Storage, log, get_ooni_root
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

    def embedded_settings(self, category, option):
        embedded_settings = os.path.join(get_ooni_root(), 'settings.ini')
        if os.path.isfile(embedded_settings):
            settings = SafeConfigParser()
            with open(embedded_settings) as fp:
                settings.readfp(fp)
            return settings.get(category, option)
        return None

    @property
    def var_lib_path(self):
        var_lib_path = self.embedded_settings("directories", "var_lib")
        if var_lib_path:
            return os.path.abspath(var_lib_path)
        return "/var/lib/ooni"

    @property
    def usr_share_path(self):
        usr_share_path = self.embedded_settings("directories", "usr_share")
        if usr_share_path:
            return os.path.abspath(usr_share_path)
        return "/usr/share/ooni"

    @property
    def data_directory_candidates(self):
        dirs = [
            self.ooni_home,
            self.var_lib_path,
            self.usr_share_path,
            os.path.join(get_ooni_root(), '..', 'data'),
            '/usr/share/'
        ]
        if os.getenv("OONI_DATA_DIR"):
            dirs.insert(0, os.getenv("OONI_DATA_DIR"))
        if self.global_options.get('datadir'):
            dirs.insert(0, abspath(expanduser(self.global_options['datadir'])))
        return dirs

    @property
    def data_directory(self):
        for target_dir in self.data_directory_candidates:
            if os.path.isdir(target_dir):
                return target_dir
        return self.var_lib_path

    @property
    def ooni_home(self):
        home = expanduser('~'+self.current_user)
        if os.getenv("HOME"):
            home = os.getenv("HOME")
        if self._custom_home:
            return self._custom_home
        else:
            return os.path.join(home, '.ooni')

    def get_data_file_path(self, file_name):
        for target_dir in self.data_directory_candidates:
            file_path = os.path.join(target_dir, file_name)
            if os.path.isfile(file_path):
                return file_path

    def set_paths(self):
        self.nettest_directory = os.path.join(get_ooni_root(), 'nettests')

        if self.advanced.inputs_dir:
            self.inputs_directory = self.advanced.inputs_dir
        else:
            self.inputs_directory = os.path.join(self.ooni_home, 'inputs')

        if self.advanced.decks_dir:
            self.decks_directory = self.advanced.decks_dir
        else:
            self.decks_directory = os.path.join(self.ooni_home, 'decks')

        self.reports_directory = os.path.join(self.ooni_home, 'reports')
        self.resources_directory = os.path.join(self.data_directory,
                                                "resources")
        if self.advanced.report_log_file:
            self.report_log_file = self.advanced.report_log_file
        else:
            self.report_log_file = os.path.join(self.ooni_home,
                                                'reporting.yml')

        if self.global_options.get('configfile'):
            config_file = self.global_options['configfile']
            self.config_file = expanduser(config_file)
        else:
            self.config_file = os.path.join(self.ooni_home, 'ooniprobe.conf')

        if 'logfile' in self.basic:
            self.basic.logfile = expanduser(self.basic.logfile.replace(
                '~', '~'+self.current_user))

    def initialize_ooni_home(self, custom_home=None):
        if custom_home:
            self._custom_home = custom_home
            self.set_paths()

        if not os.path.isdir(self.ooni_home):
            print "Ooni home directory does not exist."
            print "Creating it in '%s'." % self.ooni_home
            os.mkdir(self.ooni_home)
            os.mkdir(self.inputs_directory)
            os.mkdir(self.decks_directory)

    def _create_config_file(self):
        target_config_file = self.config_file
        print "Creating it for you in '%s'." % target_config_file
        sample_config_file = self.get_data_file_path('ooniprobe.conf.sample')

        with open(sample_config_file) as f:
            with open(target_config_file, 'w+') as w:
                for line in f:
                    if line.startswith('    logfile: '):
                        w.write('    logfile: %s\n' % (
                            os.path.join(self.ooni_home, 'ooniprobe.log'))
                        )
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
       and os.path.isfile('/etc/ooniprobe.conf'):
    config.global_options['configfile'] = '/etc/ooniprobe.conf'
    config.set_paths()

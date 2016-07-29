import os
import sys
import yaml
import getpass
from ConfigParser import SafeConfigParser

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from os.path import abspath, expanduser

from ooni.utils.net import ConnectAndCloseProtocol, connectProtocol
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
        if hasattr(sys, 'real_prefix'):
            # We are in a virtualenv use the /usr/share in the virtualenv
            return os.path.join(
                os.path.abspath(sys.prefix),
                'var', 'lib', 'ooni'
            )
        var_lib_path = self.embedded_settings("directories", "var_lib")
        if var_lib_path:
            return os.path.abspath(var_lib_path)
        return "/var/lib/ooni"

    @property
    def running_path(self):
        """
        This is the directory used to store state application data.
        It defaults to /var/lib/ooni, but if that is not writeable we will
        use the ooni_home.
        """
        var_lib_path = self.var_lib_path
        if os.access(var_lib_path, os.W_OK):
            return var_lib_path
        return self.ooni_home

    @property
    def usr_share_path(self):
        if hasattr(sys, 'real_prefix'):
            # We are in a virtualenv use the /usr/share in the virtualenv
            return os.path.join(
                os.path.abspath(sys.prefix),
                'usr', 'share', 'ooni'
            )
        usr_share_path = self.embedded_settings("directories", "usr_share")
        if usr_share_path:
            return os.path.abspath(usr_share_path)
        return "/usr/share/ooni"


    @property
    def etc_path(self):
        if hasattr(sys, 'real_prefix'):
            # We are in a virtualenv use the /usr/share in the virtualenv
            return os.path.join(
                os.path.abspath(sys.prefix),
                'usr', 'share', 'ooni'
            )
        etc_path = self.embedded_settings("directories", "etc")
        if etc_path:
            return os.path.abspath(etc_path)
        return "/etc"

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
        self.web_ui_directory = os.path.join(get_ooni_root(), 'web', 'client')

        self.inputs_directory = os.path.join(self.running_path, 'inputs')
        self.scheduler_directory = os.path.join(self.running_path, 'scheduler')
        self.decks_directory = os.path.join(self.running_path, 'decks')
        self.resources_directory = os.path.join(self.running_path, 'resources')

        self.measurements_directory = os.path.join(self.running_path,
                                                   'measurements')

        if self.global_options.get('configfile'):
            config_file = self.global_options['configfile']
            self.config_file = expanduser(config_file)
        else:
            self.config_file = os.path.join(self.ooni_home, 'ooniprobe.conf')

        if 'logfile' in self.basic:
            self.basic.logfile = expanduser(
                self.basic.logfile.replace('~', '~'+self.current_user)
            )

    def initialize_ooni_home(self, custom_home=None):
        if custom_home:
            self._custom_home = custom_home
            self.set_paths()

        ooni_home = self.ooni_home
        if not os.path.isdir(ooni_home):
            log.msg("Ooni home directory does not exist")
            log.msg("Creating it in '%s'" % ooni_home)
            os.mkdir(ooni_home)

        # also ensure the subdirectories exist
        sub_directories = [
            self.inputs_directory,
            self.decks_directory,
            self.scheduler_directory,
            self.measurements_directory,
            self.resources_directory
        ]
        for path in sub_directories:
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno != 17:
                    raise


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

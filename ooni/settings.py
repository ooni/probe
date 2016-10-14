import os
import sys
import yaml
import errno
import getpass
import platform
from ConfigParser import SafeConfigParser

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from os.path import abspath, expanduser

from ooni.utils import Storage, log, get_ooni_root

CONFIG_FILE_TEMPLATE = """\
# This is the configuration file for OONIProbe
# This file follows the YAML markup format: http://yaml.org/spec/1.2/spec.html
# Keep in mind that indentation matters.

basic:
    # Where OONIProbe should be writing its log file
    # logfile: {logfile}
    # loglevel: WARNING
    # The maximum amount of data to store on disk. Once the quota is reached,
    # we will start deleting older reports.
    # measurement_quota: 1G
privacy:
    # Should we include the IP address of the probe in the report?
    includeip: {include_ip}
    # Should we include the ASN of the probe in the report?
    includeasn: {include_asn}
    # Should we include the country as reported by GeoIP in the report?
    includecountry: {include_country}
    # Should we collect a full packet capture on the client?
    #includepcap: false
reports:
    # Should we place a unique ID inside of every report
    #unique_id: true
    # This is a prefix for each packet capture file (.pcap) per test:
    #pcap: null
    #collector: null
    # Should we be uploading reports to the collector by default?
    upload: {should_upload}
advanced:
    #debug: false
    # enable if auto detection fails
    #tor_binary: /usr/sbin/tor
    #obfsproxy_binary: /usr/bin/obfsproxy
    # For auto detection
    # interface: auto
    # Of specify a specific interface
    # interface: wlan0
    # If you do not specify start_tor, you will have to have Tor running and
    # explicitly set the control port and SOCKS port
    #start_tor: true
    # After how many seconds we should give up on a particular measurement
    #measurement_timeout: 120
    # After how many retries we should give up on a measurement
    #measurement_retries: 2
    # How many measurements to perform concurrently
    #measurement_concurrency: 4
    # After how may seconds we should give up reporting
    #reporting_timeout: 360
    # After how many retries to give up on reporting
    #reporting_retries: 5
    # How many reports to perform concurrently
    #reporting_concurrency: 7
    # If we should support communicating to plaintext backends (via HTTP)
    # insecure_backend: false
    # The preferred backend type, can be one of onion, https or cloudfront
    preferred_backend: {preferred_backend}
    # The port and address for the Web UI
    #webui_port: 8842
    #webui_address: "127.0.0.1"
    # Should the Web UI be disabled
    #disable_webui: false
tor:
    #socks_port: 8801
    #control_port: 8802
    # Specify the absolute path to the Tor bridges to use for testing
    #bridges: bridges.list
    # Specify path of the tor datadirectory.
    # This should be set to something to avoid having Tor download each time
    # the descriptors and consensus data.
    #data_dir: ~/.tor/
    #
    # This is the timeout after which we consider to to not have
    # bootstrapped properly.
    #timeout: 400
    #torrc:
        #HTTPProxy: host:port
        #HTTPProxyAuthenticator: user:password
        #HTTPSProxy: host:port
        #HTTPSProxyAuthenticator: user:password
        #UseBridges: 1
        #Bridge:
        #- "meek_lite 0.0.2.0:1 url=https://meek-reflect.appspot.com/ front=www.google.com"
        #- "meek_lite 0.0.2.0:2 url=https://d2zfqthxsdq309.cloudfront.net/ front=a0.awsstatic.com"
        #- "meek_lite 0.0.2.0:3 url=https://az786092.vo.msecnd.net/ front=ajax.aspnetcdn.com"
        #ClientTransportPlugin: "meek_lite exec /usr/bin/obfs4proxy"
"""

defaults = {
    "basic": {
        "loglevel": "WARNING",
        "logfile": "ooniprobe.log",
        "measurement_quota": "1G"
    },
    "privacy": {
        "includeip": False,
        "includeasn": True,
        "includecountry": True,
        "includepcap": False
    },
    "reports": {
        "unique_id": True,
        "pcap": None,
        "collector": None,
        "upload": True
    },
    "advanced": {
        "debug": False,
        "tor_binary": None,
        "obfsproxy_binary": None,
        "interface": "auto",
        "start_tor": True,
        "measurement_timeout": 120,
        "measurement_retries": 2,
        "measurement_concurrency": 4,
        "reporting_timeout": 360,
        "reporting_retries": 5,
        "reporting_concurrency": 7,
        "insecure_backend": False,
        "preferred_backend": "onion",
        "webui_port": 8842,
        "webui_address": "127.0.0.1",
        "webui_disabled": False
    },
    "tor": {
        "socks_port": None,
        "control_port": None,
        "bridges": None,
        "data_dir": None,
        "timeout": 400,
        "torrc": {}
    }
}

# This is the root of the ooniprobe source code tree
OONIPROBE_ROOT = get_ooni_root()

IS_VIRTUALENV = False
if hasattr(sys, 'real_prefix'):
    IS_VIRTUALENV = True

# These are the the embedded settings
_SETTINGS_INI = os.path.join(OONIPROBE_ROOT, 'settings.ini')

USR_SHARE_PATH = '/usr/share/ooni'
VAR_LIB_PATH = '/var/lib/ooni'
ETC_PATH = '/etc'

if IS_VIRTUALENV:
    _PREFIX = os.path.abspath(sys.prefix)
    VAR_LIB_PATH = os.path.join(
        _PREFIX,
        'var', 'lib', 'ooni'
    )
    USR_SHARE_PATH = os.path.join(
        _PREFIX,
        'share', 'ooni'
    )
    ETC_PATH = os.path.join(
        _PREFIX,
        'etc'
    )
elif os.path.isfile(_SETTINGS_INI):
    settings = SafeConfigParser()
    with open(_SETTINGS_INI) as fp:
        settings.readfp(fp)

    _USR_SHARE_PATH = settings.get('directories', 'usr_share')
    if _USR_SHARE_PATH is not None:
        USR_SHARE_PATH = _USR_SHARE_PATH

    _VAR_LIB_PATH = settings.get('directories', 'var_lib')
    if _VAR_LIB_PATH is not None:
        VAR_LIB_PATH = _VAR_LIB_PATH

    _ETC_PATH = settings.get('directories', 'etc')
    if _ETC_PATH is not None:
        ETC_PATH = _ETC_PATH


def _load_config_files_with_defaults(config_files, defaults):
    """
    This takes care of reading the config files in reverse order (the first
    item will have priority over the last element) and produce a
    configuration that includes ONLY the options inside of the defaults
    dictionary.

    :param config_files: a list of configuration file paths
    :param defaults: the default values for the configuration file
    :return: a configuration that is the result of reading the config files
    and joining it with the default options.
    """
    config_from_files = {}
    configuration = {}
    for config_file_path in reversed(config_files):
        if not os.path.exists(config_file_path):
            continue
        with open(config_file_path) as in_file:
            c = yaml.safe_load(in_file)
        for category in c.keys():
            if c[category] is None:
                continue
            config_from_files[category] = config_from_files.get(category, {})
            config_from_files[category].update(c[category])

    for category in defaults.keys():
        configuration[category] = {}
        for k, v in defaults[category].items():
            try:
                configuration[category][k] = config_from_files[category][k]
            except (KeyError, TypeError):
                configuration[category][k] = defaults[category][k]
    return configuration

class OConfig(object):
    _custom_home = None

    def __init__(self):
        self.current_user = getpass.getuser()

        self.global_options = {}

        self.scapyFactory = None
        self.tor_state = None

        self.logging = True

        # These are the configuration options
        self.basic = Storage()
        self.advanced = Storage()
        self.reports = Storage()
        self.tor = Storage()
        self.privacy = Storage()

        # In here we store the configuration files ordered by priority.
        # First configuration file takes priority over the others.
        self.config_files = []

        self.set_paths()

    def is_initialized(self):
        # When this is false it means that the user has not gone
        # through the steps of acquiring informed consent and
        # initializing this ooniprobe installation.
        initialized_path = os.path.join(self.running_path, 'initialized')
        return os.path.exists(initialized_path)

    def set_initialized(self):
        initialized_path = os.path.join(self.running_path, 'initialized')
        with open(initialized_path, 'w+'): pass

    @property
    def running_path(self):
        """
        This is the directory used to store state application data.
        It defaults to /var/lib/ooni, but if that is not writeable we will
        use the ooni_home.
        """
        if os.access(VAR_LIB_PATH, os.W_OK):
            return VAR_LIB_PATH
        return self.ooni_home

    @property
    def user_pid_path(self):
        return os.path.join(self.ooni_home, "twistd.pid")

    @property
    def system_pid_path(self):
        return os.path.join(VAR_LIB_PATH, "twistd.pid")

    @property
    def data_directory_candidates(self):
        dirs = [
            self.ooni_home,
            VAR_LIB_PATH,
            USR_SHARE_PATH,
            os.path.join(OONIPROBE_ROOT, '..', 'data'),
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
        return VAR_LIB_PATH

    @property
    def user_config_file_path(self):
        return os.path.join(self.running_path, 'ooniprobe.conf')

    @property
    def ooni_home(self):
        home = expanduser('~'+self.current_user)
        if os.getenv("HOME"):
            home = os.getenv("HOME")
        if self._custom_home:
            return self._custom_home
        else:
            return os.path.join(home, '.ooni')

    @property
    def web_ui_url(self):
        return "http://{0}:{1}".format(
            self.advanced.webui_address,
            self.advanced.webui_port
        )

    @property
    def platform(self):
        if os.path.exists('/etc/default/lepidopter'):
            return 'lepidopter'
        system = platform.system()
        if system == 'Darwin':
            return 'macos'
        elif system == 'Linux':
            return 'linux'
        elif system == 'Windows':
            # Really?
            return 'windows'
        return 'unknown'

    def get_data_file_path(self, file_name):
        for target_dir in self.data_directory_candidates:
            file_path = os.path.join(target_dir, file_name)
            if os.path.isfile(file_path):
                return file_path

    def set_paths(self):
        self.nettest_directory = os.path.join(OONIPROBE_ROOT, 'nettests')
        self.web_ui_directory = os.path.join(OONIPROBE_ROOT, 'ui', 'web',
                                             'client')

        self.inputs_directory = os.path.join(self.running_path, 'inputs')
        self.scheduler_directory = os.path.join(self.running_path, 'scheduler')
        self.resources_directory = os.path.join(self.running_path, 'resources')

        self.decks_available_directory = os.path.join(USR_SHARE_PATH,
                                                      'decks-available')
        self.decks_enabled_directory = os.path.join(self.running_path,
                                                    'decks-enabled')

        self.measurements_directory = os.path.join(self.running_path,
                                                   'measurements')

        self.config_files = [
            self.user_config_file_path,
            '/etc/ooniprobe.conf'
        ]
        if self.global_options.get('configfile'):
            config_file = self.global_options['configfile']
            self.config_files.insert(0, expanduser(config_file))

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
            self.decks_enabled_directory,
            self.decks_available_directory,
            self.scheduler_directory,
            self.measurements_directory,
            self.resources_directory
        ]
        for path in sub_directories:
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

    def create_config_file(self, include_ip=False, include_asn=True,
                           include_country=True, should_upload=True,
                           preferred_backend="onion"):
        self.initialize_ooni_home()
        def _bool_to_yaml(value):
            if value is True:
                return 'true'
            elif value is False:
                return 'false'
            else:
                return 'null'
        # Convert the boolean value to their YAML string representation
        include_ip = _bool_to_yaml(include_ip )
        include_asn = _bool_to_yaml(include_asn)
        include_country = _bool_to_yaml(include_country)
        should_upload = _bool_to_yaml(should_upload)

        logfile = os.path.join(self.running_path, 'ooniprobe.log')
        with open(self.user_config_file_path, 'w') as out_file:
            out_file.write(
                    CONFIG_FILE_TEMPLATE.format(
                                    logfile=logfile,
                                    include_ip=include_ip,
                                    include_asn=include_asn,
                                    include_country=include_country,
                                    should_upload=should_upload,
                                    preferred_backend=preferred_backend)
            )
        self.read_config_file()

    def read_config_file(self, check_incoherences=False):
        configuration = _load_config_files_with_defaults(
            self.config_files, defaults)

        for category in configuration.keys():
            for key, value in configuration[category].items():
                getattr(self, category)[key] = value

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
        from ooni import errors
        if len(incoherences) > 0:
            if len(incoherences) > 1:
                incoherent_pretty = ", ".join(incoherences[:-1]) + ' and ' + incoherences[-1]
            else:
                incoherent_pretty = incoherences[0]
            log.err("You must set properly %s in %s." % (incoherent_pretty,
                                                         self.config_files[0]))
            raise errors.ConfigFileIncoherent

    @defer.inlineCallbacks
    def check_tor(self):
        """
        Called only when we must start tor by director.start
        """
        from ooni.utils.net import ConnectAndCloseProtocol, connectProtocol
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

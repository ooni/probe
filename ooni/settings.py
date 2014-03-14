import os
import sys
import yaml
import getpass

from shutil import copyfile
from os.path import abspath, expanduser

from twisted.internet import reactor, threads, defer

from ooni import otime
from ooni.utils import Storage

class OConfig(object):
    def __init__(self):
        self.current_user = getpass.getuser()
        self.global_options = {}
        self.reports = Storage()
        self.scapyFactory = None
        self.tor_state = None
        # This is used to store the probes IP address obtained via Tor
        self.probe_ip = None
        # This is used to keep track of the state of the sniffer
        self.sniffer_running = None
        self.logging = True
        self.basic = Storage()
        self.advanced = Storage()
        self.tor = Storage()
        self.privacy = Storage()
        self.set_paths()
        self.initialize_ooni_home()

    def set_paths(self):
        if self.global_options.get('datadir'):
            self.data_directory = abspath(expanduser(self.global_options['datadir']))
        elif self.advanced.get('data_dir'):
            self.data_directory = self.advanced['data_dir']
        elif hasattr(sys, 'real_prefix'):
            self.data_directory = os.path.abspath(os.path.join(sys.prefix, 'share', 'ooni'))
        else:
            self.data_directory = '/usr/share/ooni/'

        self.nettest_directory = abspath(os.path.join(__file__, '..', 'nettests'))

        self.ooni_home = os.path.join(expanduser('~'+self.current_user), '.ooni')
        self.inputs_directory = os.path.join(self.ooni_home, 'inputs')
        self.decks_directory = os.path.join(self.ooni_home, 'decks')
        self.reports_directory = os.path.join(self.ooni_home, 'reports')

        if self.global_options.get('configfile'):
            config_file = self.global_options['configfile']
        else:
            config_file = os.path.join('~', '.ooni', 'ooniprobe.conf')
        self.config_file = expanduser(config_file)

    def initialize_ooni_home(self):
        if not os.path.isdir(self.ooni_home):
            print "Ooni home directory does not exist."
            print "Creating it in '%s'." % self.ooni_home
            os.mkdir(self.ooni_home)
            os.mkdir(self.inputs_directory)
            os.mkdir(self.decks_directory)
        if not os.path.isdir(self.reports_directory):
            os.mkdir(self.reports_directory)

    def _create_config_file(self):
        sample_config_file = os.path.join(self.data_directory,
                                          'ooniprobe.conf.sample')
        target_config_file = os.path.join(self.ooni_home,
                                          'ooniprobe.conf')
        print "Creating it for you in '%s'." % target_config_file
        usr_share_path = '/usr/share'
        if hasattr(sys, 'real_prefix'):
            usr_share_path = os.path.abspath(os.path.join(sys.prefix, 'share'))
        
        with open(sample_config_file) as f:
            with open(target_config_file, 'w+') as w:
                for line in f:
                    if line.startswith('    data_dir: '):
                        w.write('    data_dir: %s\n' % os.path.join(usr_share_path, 'ooni'))
                    elif line.startswith('    geoip_data_dir: '):
                        w.write('    geoip_data_dir: %s\n' % os.path.join(usr_share_path, 'GeoIP'))
                    else:
                        w.write(line)

    def read_config_file(self):
        try:
            with open(self.config_file) as f: pass
        except IOError:
            print "Configuration file does not exist."
            self._create_config_file()
            self.read_config_file()

        with open(self.config_file) as f:
            config_file_contents = '\n'.join(f.readlines())
            configuration = yaml.safe_load(config_file_contents)

            for setting in ['basic', 'advanced', 'privacy', 'tor']:
                try:
                    for k, v in configuration[setting].items():
                        getattr(self, setting)[k] = v
                except AttributeError:
                    pass
        self.set_paths()

    def generatePcapFilename(self, testDetails):
        test_name, start_time = testDetails['test_name'], testDetails['start_time']
        start_time = otime.epochToTimestamp(start_time)
        return "report-%s-%s.%s" % (test_name, start_time, "pcap")

config = OConfig()

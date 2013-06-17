import os
import yaml
from shutil import copyfile
from os.path import abspath, expanduser

from twisted.internet import reactor, threads, defer

from ooni import otime
from ooni.utils import Storage

class OConfig(object):
    def __init__(self):
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
        else:
            self.data_directory = '/usr/share/ooni/'
        self.nettest_directory = os.path.join(self.data_directory, 'nettests')

        self.ooni_home = os.path.join(expanduser('~'), '.ooni')
        self.inputs_directory = os.path.join(self.ooni_home, 'inputs')
        self.reports_directory = os.path.join(self.ooni_home, 'reports')

        if self.global_options.get('configfile'):
            config_file = global_options['configfile']
        else:
            config_file = os.path.join('~', '.ooni', 'ooniprobe.conf')
        self.config_file = expanduser(config_file)

    def initialize_ooni_home(self):
        if not os.path.isdir(self.ooni_home):
            print "Ooni home directory does not exist."
            print "Creating it in '%s'." % self.ooni_home
            os.mkdir(self.ooni_home)
            os.mkdir(self.inputs_directory)
        if not os.path.isdir(self.reports_directory):
            os.mkdir(self.reports_directory)

    def _create_config_file(self):
        sample_config_file = os.path.join(self.data_directory,
                                          'ooniprobe.conf.sample')
        target_config_file = os.path.join(self.ooni_home,
                                          'ooniprobe.conf')
        print "Creating it for you in '%s'." % target_config_file
        copyfile(sample_config_file, target_config_file)

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

    def generate_pcap_filename():
        if self.global_options.get('pcapfile'):
            self.reports.pcap = self.global_options['pcapfile']
        else:
            if self.global_options.get('test'):
                test_filename = os.path.basename(self.global_options['test'])
            else:
                test_filename = os.path.basename(self.global_options['testdeck'])

            test_name = '.'.join(test_filename.split(".")[:-1])
            frm_str = "report_%s_"+otime.timestamp()+".%s"
            self.reports.pcap = frm_str % (test_name, "pcap")

config = OConfig()

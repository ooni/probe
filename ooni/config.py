import os
import yaml

from twisted.internet import reactor, threads, defer

from ooni import otime
from ooni.utils import Storage

class TestFilenameNotSet(Exception):
    pass

def get_root_path():
    this_directory = os.path.dirname(__file__)
    root = os.path.join(this_directory, '..')
    root = os.path.abspath(root)
    return root

def createConfigFile():
    """
    XXX implement me
    """
    sample_config_file = os.path.join(get_root_path(), 'ooniprobe.conf.sample')

def generatePcapFilename():
    if cmd_line_options['pcapfile']:
        reports.pcap = cmd_line_options['pcapfile']
    else:
        if cmd_line_options['test']:
            test_filename = os.path.basename(cmd_line_options['test'])
        else:
            test_filename = os.path.basename(cmd_line_options['testdeck'])

        test_name = '.'.join(test_filename.split(".")[:-1])
        frm_str = "report_%s_"+otime.timestamp()+".%s"
        reports.pcap = frm_str % (test_name, "pcap")

class ConfigurationSetting(Storage):
    def __init__(self, key):
        config_file = os.path.join(get_root_path(), 'ooniprobe.conf')
        try:
            f = open(config_file)
        except IOError:
            createConfigFile()
            raise Exception("Unable to open config file. "\
                        "Copy ooniprobe.conf.sample to ooniprobe.conf")

        config_file_contents = '\n'.join(f.readlines())
        configuration = yaml.safe_load(config_file_contents)

        try:
            for k, v in configuration[key].items():
                self[k] = v
        except AttributeError:
            pass

basic = ConfigurationSetting('basic')
advanced = ConfigurationSetting('advanced')
privacy = ConfigurationSetting('privacy')
tor = ConfigurationSetting('tor')

data_directory = os.path.join(get_root_path(), 'data')
nettest_directory = os.path.join(get_root_path(), 'nettests')
inputs_directory = os.path.join(get_root_path(), 'inputs')

reports = Storage()
state = Storage()
scapyFactory = None
stateDict = None

# XXX refactor this to use a database
resume_lock = defer.DeferredLock()

cmd_line_options = None
resume_filename = None

# XXX-Twisted this is used to check if we have started the reactor or not. It
# is necessary because if the tests are already concluded because we have
# resumed a test session then it will call reactor.run() even though there is
# no condition that will ever stop it.
# There should be a more twisted way of doing this.
start_reactor = True
tor_state = None
tor_control = None
config_file = None
sample_config_file = None
# This is used to store the probes IP address obtained via Tor
probe_ip = None
# This is used to keep track of the state of the sniffer
sniffer_running = None

logging = True

if not resume_filename:
    resume_filename = os.path.join(get_root_path(), 'ooniprobe.resume')
    try:
        with open(resume_filename) as f: pass
    except IOError as e:
        with open(resume_filename, 'w+') as f: pass

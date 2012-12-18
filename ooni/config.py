import os
import yaml

from twisted.internet import reactor, threads, defer

from ooni import otime
from ooni.utils import Storage

reports = Storage()
scapyFactory = None
stateDict = None
state = Storage()

# XXX refactor this to use a database
resume_lock = defer.DeferredLock()

basic = None
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

def loadConfigFile():
    """
    This is a helper function that makes sure that the configuration attributes
    are singletons.
    """
    config_file = os.path.join(get_root_path(), 'ooniprobe.conf')
    try:
        f = open(config_file)
    except IOError:
        createConfigFile()
        raise Exception("Unable to open config file. "\
                    "Copy ooniprobe.conf.sample to ooniprobe.conf")

    config_file_contents = '\n'.join(f.readlines())
    configuration = yaml.safe_load(config_file_contents)

    # Process the basic configuration options
    basic = Storage()
    for k, v in configuration['basic'].items():
        basic[k] = v

    # Process the privacy configuration options
    privacy = Storage()
    for k, v in configuration['privacy'].items():
        privacy[k] = v

    # Process the advanced configuration options
    advanced = Storage()
    for k, v in configuration['advanced'].items():
        advanced[k] = v

    # Process the tor configuration options
    tor = Storage()
    try:
        for k, v in configuration['tor'].items():
            tor[k] = v
    except AttributeError:
        pass

    return basic, privacy, advanced, tor

class TestFilenameNotSet(Exception):
    pass

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

if not basic:
    # Here we make sure that we instance the config file attributes only once
    basic, privacy, advanced, tor = loadConfigFile()

if not resume_filename:
    resume_filename = os.path.join(get_root_path(), 'ooniprobe.resume')
    try:
        with open(resume_filename) as f: pass
    except IOError as e:
        with open(resume_filename, 'w+') as f: pass

# This is used to keep track of the state of the sniffer
sniffer_running = None

# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import os
import yaml

from twisted.internet import reactor, threads

from ooni.utils import otime
from ooni.utils import Storage

reports = Storage()
basic = None
cmd_line_options = None

def get_root_path():
    this_directory = os.path.dirname(__file__)
    root = os.path.join(this_directory, '..')
    root = os.path.abspath(root)
    return root

def loadConfigFile():
    """
    This is a helper function that makes sure that the configuration attributes
    are singletons.
    """
    config_file = os.path.join(get_root_path(), 'ooniprobe.conf')
    try:
        f = open(config_file)
    except IOError:
        raise Exception("Unable to open config file. "\
                    "Create a config file called ooniprobe.conf")

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
    return basic, privacy, advanced

class TestFilenameNotSet(Exception):
    pass

def generateReportFilenames():
    try:
        test_file_name = os.path.basename(cmd_line_options['test'])
    except IndexError:
        raise TestFilenameNotSet

    test_name = '.'.join(test_file_name.split(".")[:-1])
    base_filename = "%s_%s_"+otime.timestamp()+".%s"
    print "Setting yamloo to %s" % base_filename
    reports.yamloo = base_filename % (test_name, "report", "yamloo")
    reports.pcap = base_filename % (test_name, "packets", "pcap")

if not basic:
    # Here we make sure that we instance the config file attributes only once
    basic, privacy, advanced = loadConfigFile()

# This is used to keep track of the state of the sniffer
sniffer_running = None

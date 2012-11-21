# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import os
import yaml

from twisted.internet import reactor, threads

from ooni.utils import otime
from ooni.utils import Storage


def get_root_path():
    this_directory = os.path.dirname(__file__)
    root = os.path.join(this_directory, '..')
    root = os.path.abspath(root)
    return root

def oreport_filenames(file_name):
    """
    returns the filenames for the pcap file and the yamloo report

    returns
    yamloo_filename, pcap_filename
    """
    test_name = '.'.join(file_name.split(".")[:-1])
    base_filename = "%s_%s_"+otime.timestamp()+".%s"
    yamloo_filename = base_filename % (test_name, "report", "yamloo")
    pcap_filename = base_filename % (test_name, "packets", "pcap")
    return yamloo_filename, pcap_filename

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

basic = None
if not basic:
    # Here we make sure that we instance the config file attributes only once
    basic, privacy, advanced = loadConfigFile()

# This is used to keep track of the state of the sniffer
sniffer_running = None

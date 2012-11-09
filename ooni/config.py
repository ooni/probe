# -*- encoding: utf-8 -*-
#
# :authors: Arturo "hellais" Filastò <art@fuffa.org>
# :licence: see LICENSE

import os
import yaml

from twisted.internet import reactor

from ooni.utils import Storage

def get_root_path():
    this_directory = os.path.dirname(__file__)
    root = os.path.join(this_directory, '..')
    root = os.path.abspath(root)
    return root

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

threadpool = ThreadPool(0, advanced.threadpool_size)
threadpool.start()
# This is used to keep track of the state of the sniffer
sniffer_running = None

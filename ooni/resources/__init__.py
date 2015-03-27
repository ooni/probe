import os

from ooni.settings import config
from ooni.utils import unzip, gunzip

from ooni.deckgen.processors import citizenlab_test_lists
from ooni.deckgen.processors import namebench_dns_servers

__version__ = "0.1.0"

if os.access(config.var_lib_path, os.W_OK):
    resources_directory = os.path.join(config.var_lib_path,
                                       "resources")
    geoip_directory = os.path.join(config.var_lib_path,
                                   "GeoIP")
else:
    resources_directory = os.path.join(config.ooni_home,
                                       "resources")
    geoip_directory = os.path.join(config.ooni_home,
                                   "GeoIP")

inputs = {
    "namebench-dns-servers.csv": {
        "url": "https://namebench.googlecode.com/svn/trunk/config/servers.csv",
        "action": None,
        "action_args": [],
        "processor": namebench_dns_servers,
    },
    "citizenlab-test-lists.zip": {
        "url": "https://github.com/citizenlab/test-lists/archive/master.zip",
        "action": unzip,
        "action_args": [resources_directory],
        "processor": citizenlab_test_lists
    }
}

geoip = {
    "GeoLiteCity.dat.gz": {
        "url": "https://geolite.maxmind.com/download/"
               "geoip/database/GeoLiteCity.dat.gz",
        "action": gunzip,
        "action_args": [geoip_directory],
        "processor": None
    },
    "GeoIPASNum.dat.gz": {
        "url": "https://geolite.maxmind.com/download/"
               "geoip/database/asnum/GeoIPASNum.dat.gz",
        "action": gunzip,
        "action_args": [geoip_directory],
        "processor": None
    },
    "GeoIP.dat.gz": {
        "url": "https://geolite.maxmind.com/"
               "download/geoip/database/GeoLiteCountry/GeoIP.dat.gz",
        "action": gunzip,
        "action_args": [geoip_directory],
        "processor": None
    }
}

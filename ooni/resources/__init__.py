from ooni.settings import config
from ooni.utils import unzip, gunzip

from ooni.deckgen.processors import citizenlab_test_lists
from ooni.deckgen.processors import namebench_dns_servers

config.read_config_file()

__version__ = "0.0.1"

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
        "action_args": [config.resources_directory],
        "processor": citizenlab_test_lists
    }
}

geoip = {
    "GeoIPASNum.dat.gz": {
        "url": "http://www.maxmind.com/download/"
               "geoip/database/asnum/GeoIPASNum.dat.gz",
        "action": gunzip,
        "action_args": [config.advanced.geoip_data_dir],
        "processor": None
    },
    "GeoIP.dat.gz": {
        "url": "http://geolite.maxmind.com/"
               "download/geoip/database/GeoLiteCountry/GeoIP.dat.gz",
        "action": gunzip,
        "action_args": [config.advanced.geoip_data_dir],
        "processor": None
    }
}

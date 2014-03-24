from twisted.internet import defer
from twisted.trial import unittest

from ooni.tests import is_internet_connected
from ooni.settings import config
from ooni import geoip

class TestGeoIP(unittest.TestCase):
    def setUp(self):
        config.set_paths()
        config.read_config_file()
 
    def test_ip_to_location(self):
        location = geoip.IPToLocation('8.8.8.8')
        assert 'countrycode' in location
        assert 'asn' in location
        assert 'city' in location

    @defer.inlineCallbacks
    def test_probe_ip(self):
        if not is_internet_connected():
            self.skipTest("You must be connected to the internet to run this test")
        probe_ip = geoip.ProbeIP()
        res = yield probe_ip.lookup()
        assert len(res.split('.')) == 4


from twisted.internet import defer

from ooni.tests import is_internet_connected, bases
from ooni import geoip


class TestGeoIP(bases.ConfigTestCase):
    def test_ip_to_location(self):
        location = geoip.IPToLocation('8.8.8.8')
        assert 'countrycode' in location
        assert 'asn' in location
        assert 'city' in location

    @defer.inlineCallbacks
    def test_probe_ip(self):
        if not is_internet_connected():
            self.skipTest(
                "You must be connected to the internet to run this test"
            )
        probe_ip = geoip.ProbeIP()
        res = yield probe_ip.lookup()
        assert len(res.split('.')) == 4

    def test_geoip_database_version(self):
        version = geoip.database_version()
        assert 'GeoIP' in version.keys()
        assert 'GeoIPASNum' in version.keys()

        assert len(version['GeoIP']['sha256']) == 64
        assert isinstance(version['GeoIP']['timestamp'], float)
        assert len(version['GeoIPASNum']['sha256']) == 64
        assert isinstance(version['GeoIPASNum']['timestamp'], float)

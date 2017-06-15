import os
import mock
import shutil
from twisted.internet import defer
from twisted.names import client

from ooni.tests import is_internet_connected, bases
from ooni.tests.mocks import mock_dns_lookup_address
from ooni import geoip


class TestGeoIP(bases.ConfigTestCase):
    def test_ip_to_location(self):
        location = geoip.ip_to_location('8.8.8.8')
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

        with mock.patch.object(client, 'lookupAddress', side_effect=mock_dns_lookup_address()):
            address = yield probe_ip.lookup()
        assert len(address.split('.')) == 4

    @defer.inlineCallbacks
    def test_probe_ipdns_address(self):
        probe_ip = geoip.ProbeIP()

        with mock.patch.object(client, 'lookupAddress', side_effect=mock_dns_lookup_address()):
            dns_address = yield probe_ip.dns_lookup()
        assert len(dns_address.split('.')) == 4

    def test_geoip_database_version(self):
        maxmind_dir = os.path.join(self.config.resources_directory,
                                   'maxmind-geoip')
        try:
            os.mkdir(maxmind_dir)
        except OSError:
            pass
        with open(os.path.join(maxmind_dir, 'GeoIP.dat'), 'w+') as f:
            f.write("XXX")
        with open(os.path.join(maxmind_dir, 'GeoIPASNum.dat'), 'w+') as f:
            f.write("XXX")

        version = geoip.database_version()
        assert 'GeoIP' in version.keys()
        assert 'GeoIPASNum' in version.keys()

        assert len(version['GeoIP']['sha256']) == 64
        assert isinstance(version['GeoIP']['timestamp'], float)
        assert len(version['GeoIPASNum']['sha256']) == 64
        assert isinstance(version['GeoIPASNum']['timestamp'], float)

        shutil.rmtree(maxmind_dir)

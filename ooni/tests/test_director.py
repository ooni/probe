import time

from mock import patch, MagicMock

from ooni.settings import config
from ooni.director import Director
from ooni.tests.bases import ConfigTestCase

from twisted.internet import defer
from twisted.trial import unittest

from txtorcon import TorControlProtocol

proto = MagicMock()
proto.tor_protocol = TorControlProtocol()

mock_TorState = MagicMock()
# We use the instance of mock_TorState so that the mock caching will
# return the same instance when TorState is created.
mts = mock_TorState()
mts.protocol.get_conf = lambda x: defer.succeed({'SocksPort': '4242'})
mts.post_bootstrap = defer.succeed(mts)

# Set the tor_protocol to be already fired
state = MagicMock()
proto.tor_protocol.post_bootstrap = defer.succeed(state)

mock_launch_tor = MagicMock()
mock_launch_tor.return_value = defer.succeed(proto)


class TestDirector(ConfigTestCase):
    def tearDown(self):
        super(TestDirector, self).tearDown()
        config.tor_state = None

    def test_get_net_tests(self):
        director = Director()
        nettests = director.getNetTests()
        assert 'http_requests' in nettests
        assert 'dns_consistency' in nettests
        assert 'http_header_field_manipulation' in nettests
        assert 'traceroute' in nettests

    @patch('ooni.director.TorState', mock_TorState)
    @patch('ooni.director.launch_tor', mock_launch_tor)
    def test_start_tor(self):
        @defer.inlineCallbacks
        def director_start_tor():
            director = Director()
            yield director.startTor()
            assert config.tor.socks_port == 4242
            assert config.tor.control_port == 4242

        return director_start_tor()


class TestStartSniffing(unittest.TestCase):
    def setUp(self):
        self.director = Director()
        self.testDetails = {
            'test_name': 'foo',
            'start_time': time.time()
        }

        # Each NetTestCase has a name attribute
        class FooTestCase(object):
            name = 'foo'
        self.FooTestCase = FooTestCase

    def test_start_sniffing_once(self):
        with patch('ooni.settings.config.scapyFactory') as mock_scapy_factory:
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                self.director.startSniffing(self.testDetails)
                sniffer = mock_scapy_sniffer.return_value
                mock_scapy_factory.registerProtocol.assert_called_once_with(sniffer)

    def test_start_sniffing_twice(self):
        with patch('ooni.settings.config.scapyFactory') as mock_scapy_factory:
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                sniffer = mock_scapy_sniffer.return_value
                sniffer.pcapwriter.filename = 'foo1_filename'
                self.director.startSniffing(self.testDetails)
                self.assertEqual(len(self.director.sniffers), 1)

            self.testDetails = {
                'test_name': 'bar',
                'start_time': time.time()
            }
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                sniffer = mock_scapy_sniffer.return_value
                sniffer.pcapwriter.filename = 'foo2_filename'
                self.director.startSniffing(self.testDetails)
                self.assertEqual(len(self.director.sniffers), 2)

    def test_measurement_succeeded(self):
        with patch('ooni.settings.config.scapyFactory') as mock_scapy_factory:
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                self.director.startSniffing(self.testDetails)
                self.assertEqual(len(self.director.sniffers), 1)
                measurement = MagicMock()
                measurement.testInstance = self.FooTestCase()
                self.director.measurementSucceeded('awesome', measurement)
                self.assertEqual(len(self.director.sniffers), 0)
                sniffer = mock_scapy_sniffer.return_value
                mock_scapy_factory.unRegisterProtocol.assert_called_once_with(sniffer)


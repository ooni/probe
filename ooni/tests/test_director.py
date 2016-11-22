from mock import patch, MagicMock

from ooni.settings import config
from ooni.director import Director
from ooni.tests.bases import ConfigTestCase

from ooni.nettest import NetTestLoader

from twisted.internet import defer
from twisted.trial import unittest

from txtorcon import TorControlProtocol

test_failing_twice = """
from twisted.internet import defer, reactor
from ooni.nettest import NetTestCase

class TestFailingTwice(NetTestCase):
    inputs = ["spam-{}".format(idx) for idx in range(50)]

    def setUp(self):
        self.summary[self.input] = self.summary.get(self.input, 0)

    def test_a(self):
        run_count = self.summary[self.input]
        delay = float(self.input.split("-")[1])/1000
        d = defer.Deferred()
        def callback():
            self.summary[self.input] += 1
            if run_count < 3:
                d.errback(Exception("Failing"))
            else:
                d.callback(self.summary[self.input])

        reactor.callLater(delay, callback)
        return d
"""

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

    @patch('ooni.utils.onion.TorState', mock_TorState)
    @patch('ooni.utils.onion.launch_tor', mock_launch_tor)
    def test_start_tor(self):
        @defer.inlineCallbacks
        def director_start_tor():
            self.config.advanced.start_tor = True
            director = Director()
            yield director.start_tor()
            self.assertEqual(config.tor.socks_port, 4242)
            self.assertEqual(config.tor.control_port, 4242)

        return director_start_tor()

    def test_run_test_fails_twice(self):
        finished = defer.Deferred()

        def net_test_done(net_test):
            summary_items = net_test.summary.items()
            self.assertEqual(len(summary_items), 50)
            for input_name, run_count in summary_items:
                self.assertEqual(run_count, 3)
            finished.callback(None)

        net_test_loader = NetTestLoader(('spam','ham'))
        net_test_loader.loadNetTestString(test_failing_twice)
        director = Director()
        director.netTestDone = net_test_done
        director.start_net_test_loader(net_test_loader, None, no_yamloo=True)
        return finished


class TestStartSniffing(unittest.TestCase):
    def setUp(self):
        self.director = Director()
        self.testDetails = {
            'test_name': 'foo',
            'test_start_time': '2016-01-01 12:34:56'
        }

        # Each NetTestCase has a name attribute
        class FooTestCase(object):
            name = 'foo'
        self.FooTestCase = FooTestCase

    def test_start_sniffing_once(self):
        with patch('ooni.settings.config.scapyFactory') as mock_scapy_factory:
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                self.director.start_sniffing(self.testDetails)
                sniffer = mock_scapy_sniffer.return_value
                mock_scapy_factory.registerProtocol.assert_called_once_with(sniffer)

    def test_start_sniffing_twice(self):
        with patch('ooni.settings.config.scapyFactory') as mock_scapy_factory:
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                sniffer = mock_scapy_sniffer.return_value
                sniffer.pcapwriter.filename = 'foo1_filename'
                self.director.start_sniffing(self.testDetails)
                self.assertEqual(len(self.director.sniffers), 1)

            self.testDetails = {
                'test_name': 'bar',
                'test_start_time': '2016-01-01 12:34:56'
            }
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                sniffer = mock_scapy_sniffer.return_value
                sniffer.pcapwriter.filename = 'foo2_filename'
                self.director.start_sniffing(self.testDetails)
                self.assertEqual(len(self.director.sniffers), 2)

    def test_measurement_succeeded(self):
        with patch('ooni.settings.config.scapyFactory') as mock_scapy_factory:
            with patch('ooni.utils.txscapy.ScapySniffer') as mock_scapy_sniffer:
                self.director.start_sniffing(self.testDetails)
                self.assertEqual(len(self.director.sniffers), 1)
                measurement = MagicMock()
                measurement.testInstance = self.FooTestCase()
                self.director.measurementSucceeded('awesome', measurement)
                self.assertEqual(len(self.director.sniffers), 0)
                sniffer = mock_scapy_sniffer.return_value
                mock_scapy_factory.unRegisterProtocol.assert_called_once_with(sniffer)


from twisted.internet import defer
from twisted.trial import unittest

from ooni.utils import onion
from mock import Mock, patch
from txtorcon.interface import ITorControlProtocol

sample_transport_lines = {
    'fte': 'fte exec /fakebin --managed',
    'scramblesuit': 'scramblesuit exec /fakebin --log-min-severity info --log-file /log.txt managed',
    'obfs2': 'obfs2 exec /fakebin --log-min-severity info --log-file /log.txt managed',
    'obfs3': 'obfs3 exec /fakebin --log-min-severity info --log-file /log.txt managed',
    'obfs4': 'obfs4 exec /fakebin --enableLogging=true --logLevel=INFO' }


class MockTorState(object):
    def __init__(self):
        self.protocol = Mock()
        self.protocol.get_state = lambda x: 8080
        self.protocol.post_bootstrap = defer.succeed(self)

class MockSuccessTorProtocol(object):
    def __init__(self):
        self.tor_protocol = Mock(ITorControlProtocol)
        self.tor_protocol.post_bootstrap = defer.succeed(MockTorState())

class TestOnion(unittest.TestCase):
    def test_tor_details(self):
        assert isinstance(onion.tor_details, dict)
        assert onion.tor_details['version']
        assert onion.tor_details['binary']

    def test_transport_dicts(self):

        self.assertEqual(set(onion.transport_bin_name.keys()),
                         set(onion._transport_line_templates.keys()))

    def test_bridge_line(self):
        self.assertRaises(onion.UnrecognizedTransport,
            onion.bridge_line, 'rot13', '/log.txt')

        onion.find_executable = Mock(return_value=False)
        self.assertRaises(onion.UninstalledTransport,
            onion.bridge_line, 'fte', '/log.txt')

        onion.find_executable = Mock(return_value="/fakebin")
        for transport, exp_line in sample_transport_lines.iteritems():
            self.assertEqual(onion.bridge_line(transport, '/log.txt'),
                             exp_line)

        with patch.dict(onion.obfsproxy_details,
                {'version': onion.OBFSProxyVersion('0.1.12')}):
            self.assertRaises(onion.OutdatedObfsproxy,
                onion.bridge_line, 'obfs2', '/log.txt')

        with patch.dict(onion.tor_details,
                {'version': onion.TorVersion('0.2.4.20')}):
            onion.bridge_line('fte', '/log.txt')
            self.assertRaises(onion.OutdatedTor,
                onion.bridge_line, 'scramblesuit', '/log.txt')
            self.assertRaises(onion.OutdatedTor,
                onion.bridge_line, 'obfs4', '/log.txt')

        with patch.dict(onion.tor_details,
                {'version': onion.TorVersion('0.2.3.20')}):
            self.assertRaises(onion.OutdatedTor,
                onion.bridge_line, 'fte', '/log.txt')

    def test_is_onion_address(self):
        self.assertEqual(onion.is_onion_address(
            'httpo://thirteenchars123.onion'), True)

        self.assertEqual(onion.is_onion_address(
            'thirteenchars123.onion'), True)

        self.assertEqual(onion.is_onion_address(
            'http://thirteenchars123.onion'), True)

        self.assertEqual(onion.is_onion_address(
            'https://thirteenchars123.onion'), True)

        self.assertEqual(onion.is_onion_address(
            'http://thirteenchars123.com'), False)

    def test_launcher_fail_once(self):
        from ooni.utils.onion import TorLauncherWithRetries
        from txtorcon import TorConfig
        tor_config = TorConfig()
        tor_launcher = TorLauncherWithRetries(tor_config)

        self.failures = 0
        def _launch_tor_fail_once():
            self.failures += 1
            if self.failures <= 1:
                return defer.fail(Exception("Failed once"))
            return defer.succeed(MockSuccessTorProtocol())

        def _mock_setup_complete(protocol):
            self.assertIsInstance(protocol, MockSuccessTorProtocol)
            self.assertTrue(
                tor_launcher.tor_config.ClientTransportPlugin.startswith("obfs4")
            )
            tor_launcher.started.callback(None)

        tor_launcher._launch_tor = _launch_tor_fail_once
        tor_launcher._setup_complete = _mock_setup_complete
        return tor_launcher.launch()

from twisted.trial import unittest
from ooni.utils import onion
from mock import Mock

sample_transport_lines = {
    'fte': 'fte exec /fakebin --managed',
    'scramblesuit': 'scramblesuit exec /fakebin --log-min-severity info --log-file /log.txt managed',
    'obfs2': 'obfs2 exec /fakebin --log-min-severity info --log-file /log.txt managed',
    'obfs3': 'obfs3 exec /fakebin --log-min-severity info --log-file /log.txt managed',
    'obfs4': 'obfs4 exec /fakebin --enableLogging=true --logLevel=INFO' }


class TestOnion(unittest.TestCase):
    def test_tor_details(self):
        assert isinstance(onion.tor_details, dict)
        assert onion.tor_details['version']
        assert onion.tor_details['binary']
    def test_transport_dicts(self):
        self.assertEqual( set(onion.transport_bin_name.keys()),
                          set(onion._transport_line_templates.keys()) )
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

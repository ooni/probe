from twisted.trial import unittest
from ooni.utils import onion


class TestOnion(unittest.TestCase):
    def test_tor_details(self):
        assert isinstance(onion.tor_details, dict)
        assert onion.tor_details['version']
        assert onion.tor_details['binary']

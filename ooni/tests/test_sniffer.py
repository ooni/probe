from twisted.trial import unittest

from ooni.sniffer import pcapdnet_installed


class SnifferTestCase(unittest.TestCase):
    def test_pcapdnet_installed(self):
        assert pcapdnet_installed() is True

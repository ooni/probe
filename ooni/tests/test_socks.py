from twisted.trial import unittest

from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.internet import reactor
from ooni.utils.socks import TrueHeadersSOCKS5Agent

class TestSocks(unittest.TestCase):
    def test_create_agent(self):
        proxyEndpoint = TCP4ClientEndpoint(reactor, '127.0.0.1', 9050)
        agent = TrueHeadersSOCKS5Agent(reactor, proxyEndpoint=proxyEndpoint)

#
# This unittest is to verify that our usage of the twisted DNS resolver does
# not break with new versions of twisted.

from twisted.trial import unittest
from twisted.names import dns
from twisted.names.client import Resolver


class DNSTest(unittest.TestCase):
    def test_a_lookup_ooni_query(self):
        def done_query(message, *arg):
            answer = message.answers[0]
            self.assertEqual(answer.type, 1)

        dns_query = [dns.Query('ooni.nu', type=dns.A)]
        resolver = Resolver(servers=[('8.8.8.8', 53)])
        d = resolver.queryUDP(dns_query)
        d.addCallback(done_query)
        return d


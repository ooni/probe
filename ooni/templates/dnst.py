# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.names import client, dns
from twisted.names.client import Resolver

from twisted.names.error import DNSQueryRefusedError

from ooni.utils import log
from ooni.nettest import NetTestCase

class DNSTest(NetTestCase):
    name = "Base DNS Test"
    version = 0.1

    requiresRoot = False
    queryTimeout = [1]

    def _setUp(self):
        self.report['queries'] = []

    def performPTRLookup(self, address, dns_server):
        """
        Does a reverse DNS lookup on the input ip address

        :address: the IP Address as a dotted quad to do a reverse lookup on.

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))
        """
        ptr = '.'.join(address.split('.')[::-1]) + '.in-addr.arpa'
        query = [dns.Query(ptr, dns.IN, dns.PTR)]
        def gotResponse(message):
            answers = []
            name = None
            for answer in message.answers:
                if answer.type is 12:
                    name = answer.payload.name

            result = {}
            result['resolver'] = dns_server
            result['query_type'] = 'PTR'
            result['query'] = repr(query)
            result['answers'] = answers
            result['name'] = name
            self.report['queries'].append(result)
            return name

        def gotError(failure):
            log.exception(failure)
            result = {}
            result['resolver'] = dns_server
            result['query_type'] = 'PTR'
            result['query'] = repr(query)
            result['error'] = str(failure)
            return None

        resolver = Resolver(servers=[dns_server])
        d = resolver.queryUDP(query, timeout=self.queryTimeout)
        d.addCallback(gotResponse)
        d.addErrback(gotError)
        return d

    def performALookup(self, hostname, dns_server):
        """
        Performs an A lookup and returns an array containg all the dotted quad
        IP addresses in the response.

        :hostname: is the hostname to perform the A lookup on

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))
        """
        query = [dns.Query(hostname, dns.IN, dns.A)]
        def gotResponse(message):
            addrs = []
            answers = []
            for answer in message.answers:
                if answer.type is 1:
                    addr = answer.payload.dottedQuad()
                    addrs.append(addr)
                # We store the resource record and the answer payload in a
                # tuple
                r = (repr(answer), repr(answer.payload))
                answers.append(r)
            result = {}
            result['resolver'] = dns_server
            result['query_type'] = 'A'
            result['query'] = repr(query)
            result['answers'] = answers
            result['addrs'] = addrs
            self.report['queries'].append(result)
            return addrs

        def gotError(failure):
            log.exception(failure)
            result = {}
            result['resolver'] = dns_server
            result['query_type'] = 'A'
            result['query'] = repr(query)
            result['error'] = str(failure)
            return None

        resolver = Resolver(servers=[dns_server])
        d = resolver.queryUDP(query, timeout=self.queryTimeout)
        d.addCallback(gotResponse)
        d.addErrback(gotError)
        return d


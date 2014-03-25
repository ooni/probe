# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.internet.defer import TimeoutError
from twisted.names import client, dns
from twisted.names.client import Resolver

from twisted.names.error import DNSQueryRefusedError

from ooni.utils import log
from ooni.nettest import NetTestCase
from ooni.errors import failureToString

from socket import gaierror


def representAnswer(answer):
    # We store the resource record and the answer payload in a
    # tuple
    return (repr(answer), repr(answer.payload))

class DNSTest(NetTestCase):
    name = "Base DNS Test"
    version = 0.1

    requiresRoot = False
    queryTimeout = [1]

    def _setUp(self):
        super(DNSTest, self)._setUp()

        self.report['queries'] = []

    def performPTRLookup(self, address, dns_server):
        """
        Does a reverse DNS lookup on the input ip address

        :address: the IP Address as a dotted quad to do a reverse lookup on.

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))
        """
        ptr = '.'.join(address.split('.')[::-1]) + '.in-addr.arpa'
        query = [dns.Query(ptr, dns.PTR, dns.IN)]
        def gotResponse(message):
            log.debug("Lookup successful")
            log.debug(message)
            answers = []
            name = ''
            for answer in message.answers:
                if answer.type is 12:
                    name = str(answer.payload.name)
                answers.append(representAnswer(answer))

            DNSTest.addToReport(self, query, resolver=dns_server,
                    query_type = 'PTR', answers=answers, name=name)
            return name

        def gotError(failure):
            log.err("Failed to perform lookup")
            log.exception(failure)
            failure.trap(gaierror, TimeoutError)
            DNSTest.addToReport(self, query, resolver=dns_server,
                    query_type = 'PTR', failure=failure)
            return None

        resolver = Resolver(servers=[dns_server])
        d = resolver.queryUDP(query, timeout=self.queryTimeout)
        d.addCallback(gotResponse)
        d.addErrback(gotError)
        return d

    def performALookup(self, hostname, dns_server = None):
        """
        Performs an A lookup and returns an array containg all the dotted quad
        IP addresses in the response.

        :hostname: is the hostname to perform the A lookup on

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        return self.dnsLookup(hostname, 'A', dns_server)

    def performNSLookup(self, hostname, dns_server = None):
        """
        Performs a NS lookup and returns an array containg all nameservers in
        the response.

        :hostname: is the hostname to perform the NS lookup on

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        return self.dnsLookup(hostname, 'NS', dns_server)

    def performSOALookup(self, hostname, dns_server = None):
        """
        Performs a SOA lookup and returns the response (name,serial).

        :hostname: is the hostname to perform the SOA lookup on
        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        return self.dnsLookup(hostname,'SOA',dns_server)

    def dnsLookup(self, hostname, dns_type, dns_server = None):
        """
        Performs a DNS lookup and returns the response.

        :hostname: is the hostname to perform the DNS lookup on
        :dns_type: type of lookup 'NS'/'A'/'SOA'
        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))
        """
        types={'NS':dns.NS,'A':dns.A,'SOA':dns.SOA}
        dnsType=types[dns_type]
        query = [dns.Query(hostname, dnsType, dns.IN)]
        def gotResponse(message):
            addrs = []
            answers = []
            if dns_server:
                msg = message.answers
            else:
                msg = message[0]
            for answer in msg:
                if answer.type is dnsType:
                    if dnsType is dns.SOA:
                        addr = (answer.name.name,answer.payload.serial)
                    elif dnsType is dns.NS:
                        addr = answer.payload.name.name
                    elif dnsType is dns.A:
                        addr = answer.payload.dottedQuad()
                    else:
                        addr = None
                    addrs.append(addr)
                answers.append(representAnswer(answer))

            DNSTest.addToReport(self, query, resolver=dns_server, query_type=dns_type,
                        answers=answers, addrs=addrs)
            return addrs

        def gotError(failure):
            failure.trap(gaierror, TimeoutError)
            DNSTest.addToReport(self, query, resolver=dns_server, query_type=dns_type,
                        failure=failure)
            return failure

        if dns_server:
            resolver = Resolver(servers=[dns_server])
            d = resolver.queryUDP(query, timeout=self.queryTimeout)
        else:
            lookupFunction={'NS':client.lookupNameservers, 'SOA':client.lookupAuthority, 'A':client.lookupAddress}
            d = lookupFunction[dns_type](hostname)

        d.addCallback(gotResponse)
        d.addErrback(gotError)
        return d


    def addToReport(self, query, resolver=None, query_type=None,
                    answers=None, name=None, addrs=None, failure=None):
        log.debug("Adding %s to report)" % query)
        result = {}
        result['resolver'] = resolver
        result['query_type'] = query_type
        result['query'] = repr(query)
        if failure:
            result['failure'] = failureToString(failure)

        if answers:
            result['answers'] = answers
            if name:
                result['name'] = name
            if addrs:
                result['addrs'] = addrs

        self.report['queries'].append(result)

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
        query = [dns.Query(hostname, dns.A, dns.IN)]
        if dns_server:
            def gotResponse(message):
                addrs = []
                answers = []
                for answer in message.answers:
                    if answer.type is dns.A:
                        addr = answer.payload.dottedQuad()
                        addrs.append(addr)
                    answers.append(representAnswer(answer))

                DNSTest.addToReport(self, query, resolver=dns_server, query_type='A',
                        answers=answers, addrs=addrs)
                return addrs

            def gotError(failure):
                failure.trap(gaierror, TimeoutError)
                DNSTest.addToReport(self, query, resolver=dns_server, query_type='A',
                        failure=failure)
                return failure

            resolver = Resolver(servers=[dns_server])
            d = resolver.queryUDP(query, timeout=self.queryTimeout)
            d.addCallback(gotResponse)
            d.addErrback(gotError)
        else:
            def gotResponse(message):
                addrs = []
                answers = []
                for answer in message[0]:
                    if answer.type is dns.A:
                        addr = answer.payload.dottedQuad()
                        addrs.append(addr)
                    answers.append(representAnswer(answer))

                DNSTest.addToReport(self, query, resolver=dns_server, query_type='A',
                        answers=answers, addrs=addrs)
                return addrs

            def gotError(failure):
                failure.trap(gaierror, TimeoutError)
                DNSTest.addToReport(self, query, resolver=dns_server, query_type='A',
                        failure=failure)
                return failure

            d = client.lookupAddress(hostname)
            d.addCallback(gotResponse)
            d.addErrback(gotError)

        return d

    def performNSLookup(self, hostname, dns_server = None):
        """
        Performs a NS lookup and returns an array containg all nameservers in
        the response.

        :hostname: is the hostname to perform the NS lookup on

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))
        """
        query = [dns.Query(hostname, dns.NS, dns.IN)]
        if dns_server:
            def gotResponse(message):
                addrs = []
                answers = []
                for answer in message.answers:
                    if answer.type is dns.NS:
                        addr = answer.payload.name.name
                        addrs.append(addr)
                    answers.append(representAnswer(answer))

                DNSTest.addToReport(self, query, resolver=dns_server, query_type='NS',
                        answers=answers, addrs=addrs)
                return addrs

            def gotError(failure):
                failure.trap(gaierror, TimeoutError)
                DNSTest.addToReport(self, query, resolver=dns_server, query_type='NS',
                        failure=failure)
                return failure

            resolver = Resolver(servers=[dns_server])
            d = resolver.queryUDP(query, timeout=self.queryTimeout)
            d.addCallback(gotResponse)
            d.addErrback(gotError)
        else:
            def gotResponse(message):
                addrs = []
                answers = []
                for answer in message[0]:
                    if answer.type is dns.NS:
                        addr = answer.payload.name.name
                        addrs.append(addr)
                    answers.append(representAnswer(answer))

                DNSTest.addToReport(self, query, resolver=dns_server, query_type='NS',
                        answers=answers, addrs=addrs)
                return addrs

            def gotError(failure):
                failure.trap(gaierror, TimeoutError)
                DNSTest.addToReport(self, query, resolver=dns_server, query_type='NS',
                        failure=failure)
                return failure

            d = client.lookupNameservers(hostname)
            d.addCallback(gotResponse)
            d.addErrback(gotError)

        return d

    def performSOALookup(self, hostname, dns_server = None):
        """
        Performs a SOA lookup and returns the response (name,serial).

        :hostname: is the hostname to perform the NS lookup on

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))
        """
        query = [dns.Query(hostname, dns.SOA, dns.IN)]
        if dns_server:
            def gotResponse(message):
                addrs = []
                answers = []
                for answer in message.answers:
                    if answer.type is dns.SOA:
                        addr = (answer.name.name,answer.payload.serial)
                        addrs.append(addr)
                    answers.append(representAnswer(answer))

                DNSTest.addToReport(self, query, resolver=dns_server, query_type='SOA',
                        answers=answers, addrs=addrs)
                return addrs

            def gotError(failure):
                failure.trap(gaierror, TimeoutError)
                DNSTest.addToReport(self, query, resolver=dns_server, query_type='SOA',
                        failure=failure)
                return failure

            resolver = Resolver(servers=[dns_server])
            d = resolver.queryUDP(query, timeout=self.queryTimeout)
            d.addCallback(gotResponse)
            d.addErrback(gotError)
        else:
            def gotResponse(message):
                addrs = []
                answers = []
                for answer in message[0]:
                    if answer.type is dns.SOA:
                        addr = (answer.name.name,answer.payload.serial)
                        addrs.append(addr)
                    answers.append(representAnswer(answer))

                DNSTest.addToReport(self, query, resolver=dns_server, query_type='SOA',
                        answers=answers, addrs=addrs)
                return addrs

            def gotError(failure):
                failure.trap(gaierror, TimeoutError)
                DNSTest.addToReport(self, query, resolver=dns_server, query_type='SOA',
                        failure=failure)
                return failure

            d = client.lookupAuthority(hostname)
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

# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import udp, error, base
from twisted.internet.defer import TimeoutError
from twisted.names import client, dns
from twisted.names.client import Resolver

from ooni.utils import log
from ooni.nettest import NetTestCase
from ooni.errors import failureToString

import socket
from socket import gaierror

dns.DNSDatagramProtocol.noisy = False

def _bindSocket(self):
    """
    _bindSocket taken from Twisted 13.1.0 to suppress logging.
    """
    try:
        skt = self.createInternetSocket()
        skt.bind((self.interface, self.port))
    except socket.error as le:
        raise error.CannotListenError(self.interface, self.port, le)

    # Make sure that if we listened on port 0, we update that to
    # reflect what the OS actually assigned us.
    self._realPortNumber = skt.getsockname()[1]

    # Here we remove the logging.
    # log.msg("%s starting on %s" % (
    #         self._getLogPrefix(self.protocol), self._realPortNumber))

    self.connected = 1
    self.socket = skt
    self.fileno = self.socket.fileno
udp.Port._bindSocket = _bindSocket

def connectionLost(self, reason=None):
    """
    Taken from Twisted 13.1.0 to suppress log.msg printing.
    """
    # Here we remove the logging.
    # log.msg('(UDP Port %s Closed)' % self._realPortNumber)
    self._realPortNumber = None
    base.BasePort.connectionLost(self, reason)
    self.protocol.doStop()
    self.socket.close()
    del self.socket
    del self.fileno
    if hasattr(self, "d"):
        self.d.callback(None)
        del self.d
udp.Port.connectionLost = connectionLost

def representAnswer(answer):
    answer_types = {
        dns.SOA: 'SOA',
        dns.NS: 'NS',
        dns.PTR: 'PTR',
        dns.A: 'A',
        dns.CNAME: 'CNAME',
        dns.MX: 'MX'
    }
    answer_type = answer_types.get(answer.type, 'unknown')
    represented_answer = {
        "answer_type": answer_type
    }
    if answer_type is 'SOA':
        represented_answer['ttl'] = answer.payload.ttl
        represented_answer['hostname'] = answer.payload.mname.name
        represented_answer['responsible_name'] = answer.payload.rname.name
        represented_answer['serial_number'] = answer.payload.serial
        represented_answer['refresh_interval'] = answer.payload.refresh
        represented_answer['retry_interval'] = answer.payload.retry
        represented_answer['minimum_ttl'] = answer.payload.minimum
        represented_answer['expiration_limit'] = answer.payload.expire
    elif answer_type in ['NS', 'PTR', 'CNAME']:
        represented_answer['hostname'] = answer.payload.name.name
    elif answer_type is 'A':
        represented_answer['ipv4'] = answer.payload.dottedQuad()
    return represented_answer

class DNSTest(NetTestCase):
    name = "Base DNS Test"
    version = "0.2.0"

    requiresRoot = False
    queryTimeout = [1]

    def _setUp(self):
        super(DNSTest, self)._setUp()

        self.report['queries'] = []

    def performPTRLookup(self, address, dns_server = None):
        """
        Does a reverse DNS lookup on the input ip address

        :address: the IP Address as a dotted quad to do a reverse lookup on.

        :dns_server: is the dns_server that should be used for the lookup as a
                     tuple of ip port (ex. ("127.0.0.1", 53))

                     if None, system dns settings will be used
        """
        ptr = '.'.join(address.split('.')[::-1]) + '.in-addr.arpa'
        return self.dnsLookup(ptr, 'PTR', dns_server)

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
        types = {
            'NS': dns.NS,
            'A': dns.A,
            'SOA': dns.SOA,
            'PTR': dns.PTR
        }
        dnsType = types[dns_type]
        query = [dns.Query(hostname, dnsType, dns.IN)]
        def gotResponse(message):
            log.debug(dns_type + " Lookup successful")
            log.debug(str(message))

            if dns_server:
                msg = message.answers
            else:
                msg = message[0]

            answers = []
            addrs = []
            for answer in msg:
                addr = None
                if answer.type is dns.SOA:
                    addr = (answer.name.name,answer.payload.serial)
                elif answer.type in [dns.NS, dns.PTR, dns.CNAME]:
                    addr = answer.payload.name.name
                elif answer.type is dns.A:
                    addr = answer.payload.dottedQuad()
                else:
                    log.debug("Unidentified answer %s" % answer)
                addrs.append(addr)
                answers.append(representAnswer(answer))

            if dns_type == 'SOA':
                for authority in message.authority:
                    answers.append(representAnswer(authority))

            DNSTest.addToReport(self, query, resolver=dns_server,
                                query_type=dns_type, answers=answers)
            return addrs

        def gotError(failure):
            failure.trap(gaierror, TimeoutError)
            DNSTest.addToReport(self, query, resolver=dns_server,
                                query_type=dns_type, failure=failure)
            return failure

        if dns_server:
            resolver = Resolver(servers=[dns_server])
            d = resolver.queryUDP(query, timeout=self.queryTimeout)
        else:
            lookupFunction = {
                'NS': client.lookupNameservers,
                'SOA': client.lookupAuthority,
                'A': client.lookupAddress,
                'PTR': client.lookupPointer
            }
            d = lookupFunction[dns_type](hostname)

        d.addCallback(gotResponse)
        d.addErrback(gotError)
        return d

    def addToReport(self, query, resolver=None, query_type=None,
                    answers=None, failure=None):
        log.debug("Adding %s to report)" % query)
        result = {
            'resolver_hostname': None,
            'resolver_port': None
        }
        if resolver is not None and len(resolver) == 2:
            result['resolver_hostname'] = resolver[0]
            result['resolver_port'] = resolver[1]
        result['query_type'] = query_type
        result['hostname'] = str(query[0].name)
        result['failure'] = None
        if failure:
            result['failure'] = failureToString(failure)

        result['answers'] = []
        if answers:
            result['answers'] = answers

        self.report['queries'].append(result)

# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.python import usage

from scapy.all import IP, UDP, DNS, DNSQR

from ooni.templates import scapyt
from ooni.utils import log


class UsageOptions(usage.Options):
    optParameters = [
        ['resolver', 'r', None,
         'Specify the resolver that should be used for DNS queries (ip:port).'],
        ['hostname', 'h', None, 'Specify the hostname of a censored site.'],
        ['backend', 'b', None,
         'Specify the IP address of a good DNS resolver (ip:port).']]


class DNSSpoof(scapyt.ScapyTest):
    name = "DNS Spoof"
    description = "Used to validate if the type of censorship " \
                  "happening is DNS spoofing or not."
    author = "Arturo Filastò"
    version = "0.0.1"
    timeout = 2

    usageOptions = UsageOptions

    requiredTestHelpers = {'backend': 'dns'}
    requiredOptions = ['hostname', 'resolver']
    requiresRoot = True
    requiresTor = False

    def setUp(self):
        self.resolverAddr, self.resolverPort = self.localOptions['resolver'].split(':')
        self.resolverPort = int(self.resolverPort)

        self.controlResolverAddr, self.controlResolverPort = self.localOptions['backend'].split(':')
        self.controlResolverPort = int(self.controlResolverPort)

        self.hostname = self.localOptions['hostname']

    def postProcessor(self, measurements):
        """
        This is not tested, but the concept is that if the two responses
        match up then spoofing is occurring.
        """
        try:
            test_answer = self.report['answered_packets'][0][UDP]
            control_answer = self.report['answered_packets'][1][UDP]
        except IndexError:
            self.report['spoofing'] = 'no_answer'
        else:
            if test_answer == control_answer:
                self.report['spoofing'] = False
            else:
                self.report['spoofing'] = True
        return self.report

    @defer.inlineCallbacks
    def test_a_lookup(self):
        question = IP(dst=self.resolverAddr) / \
                   UDP() / \
                   DNS(rd=1, qd=DNSQR(qtype="A", qclass="IN", qname=self.hostname))
        log.msg("Performing query to %s with %s:%s" %
                (self.hostname, self.resolverAddr, self.resolverPort))
        yield self.sr1(question)

    @defer.inlineCallbacks
    def test_control_a_lookup(self):
        question = IP(dst=self.controlResolverAddr) / \
                   UDP() / \
                   DNS(rd=1, qd=DNSQR(qtype="A", qclass="IN", qname=self.hostname))
        log.msg("Performing query to %s with %s:%s" %
                (self.hostname, self.controlResolverAddr, self.controlResolverPort))
        yield self.sr1(question)

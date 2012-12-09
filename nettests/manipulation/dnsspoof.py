from twisted.internet import defer
from twisted.python import usage

from scapy.all import IP, UDP, DNS, DNSQR

from ooni.templates import scapyt
from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [['resolver', 'r', None,
                    'Specify the resolver that should be used for DNS queries (ip:port)'],
                    ['hostname', 'h', None,
                        'Specify the hostname of a censored site'],
                    ['backend', 'b', '8.8.8.8:53',
                        'Specify the IP address of a good DNS resolver (ip:port)']
                    ]


class DNSSpoof(scapyt.ScapyTest):
    name = "DNS Spoof"
    timeout = 2

    usageOptions = UsageOptions

    requiredOptions = ['hostname', 'resolver']

    def setUp(self):
        self.resolverAddr, self.resolverPort = self.localOptions['resolver'].split(':')
        self.resolverPort = int(self.resolverPort)

        self.controlResolverAddr, self.controlResolverPort = self.localOptions['backend'].split(':')
        self.controlResolverPort = int(self.controlResolverPort)

        self.hostname = self.localOptions['hostname']

    def postProcessor(self, report):
        """
        This is not tested, but the concept is that if the two responses
        match up then spoofing is occuring.
        """
        try:
            test_answer = report['test_a_lookup']['answered_packets'][0][1]
            control_answer = report['test_control_a_lookup']['answered_packets'][0][1]
        except IndexError:
            self.report['spoofing'] = 'no_answer'
            return

        if test_answer[UDP] == control_answer[UDP]:
                self.report['spoofing'] = True
        else:
            self.report['spoofing'] = False
        return

    @defer.inlineCallbacks
    def test_a_lookup(self):
        question = IP(dst=self.resolverAddr)/UDP()/DNS(rd=1,
                qd=DNSQR(qtype="A", qclass="IN", qname=self.hostname))
        log.msg("Performing query to %s with %s:%s" % (self.hostname, self.resolverAddr, self.resolverPort))
        yield self.sr1(question)

    @defer.inlineCallbacks
    def test_control_a_lookup(self):
        question = IP(dst=self.controlResolverAddr)/UDP()/DNS(rd=1,
                qd=DNSQR(qtype="A", qclass="IN", qname=self.hostname))
        log.msg("Performing query to %s with %s:%s" % (self.hostname,
            self.controlResolverAddr, self.controlResolverPort))
        yield self.sr1(question)



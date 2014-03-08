# -*- encoding: utf-8 -*-

from twisted.python import usage
from twisted.internet import defer, reactor

from ooni.templates import scapyt
from itertools import chain

from scapy.all import *

from ooni.utils import log
from ooni.utils.txscapy import MPTraceroute
from ooni.settings import config

class UsageOptions(usage.Options):
    optParameters = [
                    ['backend', 'b', None, 'Test backend to use'],
                    ['timeout', 't', 5, 'The timeout for the traceroute test'],
                    ['maxttl', 'm', 30, 'The maximum value of ttl to set on packets'],
                    ['dstport', 'd', None, 'Specify a single destination port. May be repeated.'],
                    ['interval', 'i', None, 'Specify the inter-packet delay in seconds'],
                    ['numPackets', 'n', None, 'Specify the number of packets to send per hop'],
                    ]

class TracerouteTest(scapyt.BaseScapyTest):
    name = "Multi Protocol Traceroute Test"
    
    description = "Performs a UDP, TCP, ICMP traceroute with destination port number set to 0, 22, 23, 53, 80, 123, 443, 8080 and 65535"

    requiredTestHelpers = {'backend': 'traceroute'}
    requiresRoot = True
    requiresTor = False

    usageOptions = UsageOptions
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]
    version = "0.3"

    def setUp(self):
        self.st = MPTraceroute()
        if self.localOptions['maxttl']:
            self.st.ttl_max = int(self.localOptions['maxttl'])
        if self.localOptions['dstport']:
            self.st.dst_ports = [int(self.localOptions['dstport'])]
        if self.localOptions['interval']:
            self.st.interval = float(self.localOptions['interval'])

        config.scapyFactory.registerProtocol(self.st)

        self.report['test_tcp_traceroute'] = dict([('hops_%d' % d,[]) for d in self.dst_ports])
        self.report['test_udp_traceroute'] = dict([('hops_%d' % d,[]) for d in self.dst_ports])
        self.report['test_icmp_traceroute'] = {'hops': []}

    def test_icmp_traceroute(self):
        return self.st.ICMPTraceroute(self.localOptions['backend'])

    def test_tcp_traceroute(self):
        return self.st.TCPTraceroute(self.localOptions['backend'])

    def test_udp_traceroute(self):
        return self.st.UDPTraceroute(self.localOptions['backend'])

    def postProcessor(self, measurements):
        # should be called after all deferreds have calledback
        self.st.stopListening()
        self.st.matchResponses()

        if measurements[0][1].result == self.st:
            for packet in self.st.sent_packets:
                self.report['sent_packets'].append(packet)
            for packet in self.st.matched_packets.values():
                self.report['answered_packets'].extend(packet)

            for ttl in xrange(self.st.ttl_min, self.st.ttl_max):
                matchedPackets = filter(lambda x: x.ttl == ttl, self.st.matched_packets.keys())
                for packet in matchedPackets:
                    for response in self.st.matched_packets[packet]:
                        self.addToReport(packet, response)
        return self.report

    def addToReport(self, packet, response):
        p = {6: 'tcp', 17: 'udp', 1: 'icmp'}
        if packet.proto == 1:
            self.report['test_icmp_traceroute']['hops'].append({'ttl': packet.ttl, 
                                                                'rtt': response.time - packet.time,
                                                                'address': response.src})
        elif packet.proto == 6:
            self.report['test_tcp_traceroute']['hops_%s' % packet.dport].append({'ttl': packet.ttl,
                                                                                 'rtt': response.time - packet.time,
                                                                                 'address': response.src,
                                                                                 'sport': response.sport})
        else:
            self.report['test_udp_traceroute']['hops_%s' % packet.dport].append({'ttl': packet.ttl,
                                                                                 'rtt': response.time - packet.time,
                                                                                 'address': response.src,
                                                                                 'sport': response.sport})

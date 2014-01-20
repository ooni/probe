# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage
from twisted.internet import defer, reactor

from ooni.templates import scapyt
from itertools import chain

from scapy.all import *

from ooni.utils import log
from ooni.utils.txscapy import ScapyTraceroute
from ooni.settings import config

class UsageOptions(usage.Options):
    optParameters = [
                    ['backend', 'b', None, 'Test backend to use'],
                    ['timeout', 't', 5, 'The timeout for the traceroute test'],
                    ['maxttl', 'm', 30, 'The maximum value of ttl to set on packets'],
                    ['srcport', 'p', None, 'Set the source port to a specific value (only applies to TCP and UDP)']
                    ]

class TracerouteTest(scapyt.BaseScapyTest):
    name = "Multi Protocol Traceroute Test"
    description = "Performs a UDP, TCP, ICMP traceroute with destination port number set to 0, 22, 23, 53, 80, 123, 443, 8080 and 65535"
    requiredTestHelpers = {'backend': 'traceroute'}
    usageOptions = UsageOptions
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]
    timeout = 5

    def setUp(self):
        self.st = ScapyTraceroute()
        if self.localOptions['maxttl']:
            self.st.ttl_max = int(self.localOptions['maxttl'])
        config.scapyFactory.registerProtocol(self.st)
        self.done = defer.Deferred()
        self.tcp = self.udp = self.icmp = None

    def test_icmp_traceroute(self):
        self.st.ICMPTraceroute(self.localOptions['backend'])
        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self.st)
        return d

    def test_tcp_traceroute(self):
        self.st.TCPTraceroute(self.localOptions['backend'])
        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self.st)
        return d

    def test_udp_traceroute(self):
        self.st.UDPTraceroute(self.localOptions['backend'])
        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self.st)
        return d

    def postProcessor(self, measurements):
        # should be called after all deferreds have calledback
        self.st.stopListening()
        self.st.matchResponses()

        if measurements[0][1].result == self.st:
            for packet in self.st.sent_packets:
                self.report['sent_packets'].append(packet)
            self.report['answered_packets'] = self.st.matched_packets.items()
            self.report['received_packets'] = self.st.received_packets.values()

            # display responses by hop:
            self.report['hops'] = {}
            for i in xrange(self.st.ttl_min, self.st.ttl_max):
                self.report['hops'][i] = []
                matchedPackets = filter(lambda x: x.ttl == i, self.st.matched_packets.keys())
                routers = {}
                for packet in matchedPackets:
                    for pkt in self.st.matched_packets[packet]:
                        router = pkt.src
                        if router in routers:
                            routers[router].append(pkt)
                        else:
                            routers[router] = [pkt]
                for router in routers.keys():
                    self.report['hops'][i].append(router)
        return self.report

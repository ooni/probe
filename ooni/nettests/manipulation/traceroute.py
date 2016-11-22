# -*- encoding: utf-8 -*-

from twisted.internet import defer
from twisted.python import usage

from ooni.templates import scapyt

from ooni.utils import log
from ooni.utils.txscapy import MPTraceroute
from ooni.settings import config


class UsageOptions(usage.Options):
    optParameters = [
                    ['backend', 'b', None, 'Test backend to use.'],
                    ['timeout', 't', 5, 'The timeout for the traceroute test.'],
                    ['maxttl', 'm', 30,
                     'The maximum value of ttl to set on packets.'],
                    ['dstport', 'd', None,
                     'Specify a single destination port. May be repeated.'],
                    ['interval', 'i', None,
                     'Specify the inter-packet delay in seconds.'],
                    ['numPackets', 'n', None,
                     'Specify the number of packets to send per hop.'],
        ]


class Traceroute(scapyt.BaseScapyTest):
    name = "Traceroute"
    description = "Performs a UDP, TCP, ICMP traceroute with destination port number "\
                  "set to 0, 22, 23, 53, 80, 123, 443, 8080 and 65535."

    requiredTestHelpers = {'backend': 'traceroute'}
    requiredOptions = ['backend']
    requiresRoot = True
    requiresTor = False

    usageOptions = UsageOptions
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]
    version = "0.3"

    def setUp(self):
        self.report['test_tcp_traceroute'] = dict(
            [('hops_%d' % d, []) for d in self.dst_ports])
        self.report['test_udp_traceroute'] = dict(
            [('hops_%d' % d, []) for d in self.dst_ports])
        self.report['test_icmp_traceroute'] = {'hops': []}

    @defer.inlineCallbacks
    def run_traceroute(self, protocol):
        st = MPTraceroute()
        if self.localOptions['maxttl']:
            st.ttl_max = int(self.localOptions['maxttl'])
        if self.localOptions['dstport']:
            st.dst_ports = [int(self.localOptions['dstport'])]
        if self.localOptions['interval']:
            st.interval = float(self.localOptions['interval'])
        log.msg("Running %s traceroute towards %s" % (protocol,
                                                      self.localOptions['backend']))
        log.msg("This will take about %s seconds" % st.timeout)
        config.scapyFactory.registerProtocol(st)
        traceroute = getattr(st, protocol + 'Traceroute')
        yield traceroute(self.localOptions['backend'])
        st.stopListening()
        st.matchResponses()
        for packet in st.sent_packets:
            self.report['sent_packets'].append(scapyt.representPacket(packet))
        for packet in st.matched_packets.values():
            self.report['answered_packets'].append(scapyt.representPacket(packet))

        for ttl in xrange(st.ttl_min, st.ttl_max):
            matchedPackets = filter(
                lambda x: x.ttl == ttl,
                st.matched_packets.keys())
            for packet in matchedPackets:
                for response in st.matched_packets[packet]:
                    self.addToReport(packet, response)

    def test_icmp_traceroute(self):
        return self.run_traceroute('ICMP')

    def test_tcp_traceroute(self):
        return self.run_traceroute('TCP')

    def test_udp_traceroute(self):
        return self.run_traceroute('UDP')

    def addToReport(self, packet, response):
        if packet.proto == 1:
            self.report['test_icmp_traceroute']['hops'].append(
                {'ttl': packet.ttl, 'rtt': response.time - packet.time,
                 'address': response.src})
        elif packet.proto == 6:
            self.report['test_tcp_traceroute'][
                'hops_%s' % packet.dport].append(
                {'ttl': packet.ttl, 'rtt': response.time - packet.time,
                 'address': response.src, 'sport': response.sport})
        else:
            self.report['test_udp_traceroute'][
                'hops_%s' % packet.dport].append(
                {'ttl': packet.ttl, 'rtt': response.time - packet.time,
                 'address': response.src, 'sport': response.sport})

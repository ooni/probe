# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage
from twisted.internet import defer

from ooni.templates import scapyt

from scapy.all import *

from ooni.utils import log

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
    author = "Arturo Filastò"
    version = "0.2"

    requiredTestHelpers = {'backend': 'traceroute'}
    usageOptions = UsageOptions
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]

    def setUp(self):
        def get_sport(protocol):
            if self.localOptions['srcport']:
                return int(self.localOptions['srcport'])
            else:
                return random.randint(1024, 65535)

        self.get_sport = get_sport
        self.report['test_tcp_traceroute'] = {}
        self.report['test_udp_traceroute'] = {}
        self.report['test_icmp_traceroute'] = {}

    def max_ttl_and_timeout(self):
        max_ttl = int(self.localOptions['maxttl'])
        timeout = int(self.localOptions['timeout'])
        self.report['max_ttl'] = max_ttl
        self.report['timeout'] = timeout
        return max_ttl, timeout

    def test_tcp_traceroute(self):
        """
        Does a traceroute to the destination by sending TCP SYN packets
        with TTLs from 1 until max_ttl.
        """
        def finished(packets, port):
            log.msg("Finished running TCP traceroute test on port %s" % port)
            answered, unanswered = packets
            self.report['test_tcp_traceroute']['hops_'+str(port)] = []

            sent = []
            sent.extend(unanswered)
            received_by_id = dict()
            for snd,rcv in answered:
                if snd not in sent:
                    sent.append(snd)
                if rcv.src == snd.dst:
                    received_by_id[snd.id] = rcv
                else:
	            received_by_id[rcv.payload[1].id] = rcv

            for snd in sorted(sent, key=lambda x: x.ttl):
                if snd.id in received_by_id:
                    rcv = received_by_id[snd.id]
                    report = {'ttl': snd.ttl,
                            'address': rcv.src,
                            'rtt': rcv.time - snd.time,
                            'sport': snd[TCP].sport,
                    }
                    self.report['test_tcp_traceroute']['hops_'+str(port)].append(report)

        max_ttl, timeout = self.max_ttl_and_timeout()
        d = defer.Deferred()
        for port in self.dst_ports:
            d.addCallback(lambda x, port=port: IP(dst=self.localOptions['backend'],
                        ttl=(1,max_ttl),id=RandShort())/TCP(flags=0x2, dport=port,
                        sport=self.get_sport('tcp')))
            d.addCallback(self.sr, timeout)
            d.addCallback(finished, port)
        d.callback(True)
        return d

    def test_udp_traceroute(self):
        """
        Does a traceroute to the destination by sending UDP packets with empty
        payloads with TTLs from 1 until max_ttl.
        """
        def finished(packets, port):
            log.msg("Finished running UDP traceroute test on port %s" % port)
            answered, unanswered = packets
            self.report['test_udp_traceroute']['hops_'+str(port)] = []

            sent = []
            sent.extend(unanswered)
            received_by_id = dict()
            for snd,rcv in answered:
                if snd not in sent:
                    sent.append(snd)
                if rcv.src == snd.dst:
                    received_by_id[snd.id] = rcv
                else:
                    received_by_id[rcv.payload[1].id] = rcv

            for snd in sorted(sent, key=lambda x: x.ttl):
                if snd.id in received_by_id:
                    rcv = received_by_id[snd.id]
                    report = {'ttl': snd.ttl,
                            'address': rcv.src,
                            'rtt': rcv.time - snd.time,
                            'sport': snd[UDP].sport,
                    }
                    self.report['test_udp_traceroute']['hops_'+str(port)].append(report)

        max_ttl, timeout = self.max_ttl_and_timeout()
        d = defer.Deferred()
        for port in self.dst_ports:
            d.addCallback(lambda x, port=port: IP(dst=self.localOptions['backend'],
                        ttl=(1,max_ttl),id=RandShort())/UDP(dport=port,
                        sport=self.get_sport('udp')))
            d.addCallback(self.sr, timeout)
            d.addCallback(finished, port)
        d.callback(True)
        return d

    def test_icmp_traceroute(self):
        """
        Does a traceroute to the destination by sending ICMP echo request
        packets with TTLs from 1 until max_ttl.
        """
        def finished(packets):
            log.msg("Finished running ICMP traceroute test")
            answered, unanswered = packets
            self.report['test_icmp_traceroute']['hops'] = []

            sent = []
            sent.extend(unanswered)
            received_by_id = dict()
            for snd,rcv in answered:
                if snd not in sent:
                    sent.append(snd)
                if rcv.src == snd.dst:
                    received_by_id[snd.id] = rcv
                else:
	            received_by_id[rcv.payload[1].id] = rcv

            for snd in sorted(sent, key=lambda x: x.ttl):
                if snd.id in received_by_id:
                    rcv = received_by_id[snd.id]
                    report = {'ttl': snd.ttl,
                            'address': rcv.src,
                            'rtt': rcv.time - snd.time
                    }
                    self.report['test_icmp_traceroute']['hops'].append(report)
        max_ttl, timeout = self.max_ttl_and_timeout()
        packets = IP(dst=self.localOptions['backend'],
                    ttl=(1,max_ttl), id=RandShort())/ICMP()

        d = self.sr(packets, timeout=timeout)
        d.addCallback(finished)
        return d


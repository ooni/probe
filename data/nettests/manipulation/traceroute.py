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
                    ['backend', 'b', '8.8.8.8', 'Test backend to use'],
                    ['timeout', 't', 5, 'The timeout for the traceroute test'],
                    ['maxttl', 'm', 30, 'The maximum value of ttl to set on packets'],
                    ['srcport', 'p', None, 'Set the source port to a specific value (only applies to TCP and UDP)']
                    ]

class TracerouteTest(scapyt.BaseScapyTest):
    name = "Multi Protocol Traceroute Test"
    author = "Arturo Filastò"
    version = "0.1.1"

    usageOptions = UsageOptions
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]

    def setUp(self):
        def get_sport(protocol):
            if self.localOptions['srcport']:
                return int(self.localOptions['srcport'])
            else:
                return random.randint(1024, 65535)

        self.get_sport = get_sport

    def max_ttl_and_timeout(self):
        max_ttl = int(self.localOptions['maxttl'])
        timeout = int(self.localOptions['timeout'])
        self.report['max_ttl'] = max_ttl
        self.report['timeout'] = timeout
        return max_ttl, timeout


    def postProcessor(self, report):
        tcp_hops = report['test_tcp_traceroute']
        udp_hops = report['test_udp_traceroute']
        icmp_hops = report['test_icmp_traceroute']


    def test_tcp_traceroute(self):
        """
        Does a traceroute to the destination by sending TCP SYN packets
        with TTLs from 1 until max_ttl.
        """
        def finished(packets, port):
            log.debug("Finished running TCP traceroute test on port %s" % port)
            answered, unanswered = packets
            self.report['hops_'+str(port)] = []
            for snd, rcv in answered:
                try:
                    sport = snd[UDP].sport
                except IndexError:
                    log.err("Source port for this traceroute was not found. This is probably a bug")
                    sport = -1

                report = {'ttl': snd.ttl,
                        'address': rcv.src,
                        'rtt': rcv.time - snd.time,
                        'sport': sport
                }
                log.debug("%s: %s" % (port, report))
                self.report['hops_'+str(port)].append(report)

        dl = []
        max_ttl, timeout = self.max_ttl_and_timeout()
        for port in self.dst_ports:
            packets = IP(dst=self.localOptions['backend'],
                    ttl=(1,max_ttl),id=RandShort())/TCP(flags=0x2, dport=port,
                            sport=self.get_sport('tcp'))

            d = self.sr(packets, timeout=timeout)
            d.addCallback(finished, port)
            dl.append(d)
        return defer.DeferredList(dl)

    def test_udp_traceroute(self):
        """
        Does a traceroute to the destination by sending UDP packets with empty
        payloads with TTLs from 1 until max_ttl.
        """
        def finished(packets, port):
            log.debug("Finished running UDP traceroute test on port %s" % port)
            answered, unanswered = packets
            self.report['hops_'+str(port)] = []
            for snd, rcv in answered:
                report = {'ttl': snd.ttl,
                        'address': rcv.src,
                        'rtt': rcv.time - snd.time,
                        'sport': snd[UDP].sport
                }
                log.debug("%s: %s" % (port, report))
                self.report['hops_'+str(port)].append(report)
        dl = []
        max_ttl, timeout = self.max_ttl_and_timeout()
        for port in self.dst_ports:
            packets = IP(dst=self.localOptions['backend'],
                    ttl=(1,max_ttl),id=RandShort())/UDP(dport=port,
                            sport=self.get_sport('udp'))

            d = self.sr(packets, timeout=timeout)
            d.addCallback(finished, port)
            dl.append(d)
        return defer.DeferredList(dl)

    def test_icmp_traceroute(self):
        """
        Does a traceroute to the destination by sending ICMP echo request
        packets with TTLs from 1 until max_ttl.
        """
        def finished(packets):
            log.debug("Finished running ICMP traceroute test")
            answered, unanswered = packets
            self.report['hops'] = []
            for snd, rcv in answered:
                report = {'ttl': snd.ttl,
                        'address': rcv.src,
                        'rtt': rcv.time - snd.time
                }
                log.debug("%s" % (report))
                self.report['hops'].append(report)
        dl = []
        max_ttl, timeout = self.max_ttl_and_timeout()
        packets = IP(dst=self.localOptions['backend'],
                    ttl=(1,max_ttl), id=RandShort())/ICMP()

        d = self.sr(packets, timeout=timeout)
        d.addCallback(finished)
        return d


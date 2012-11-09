# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage

from ooni.utils import log
from ooni.templates import scapyt

from scapy.all import *

class UsageOptions(usage.Options):
    optParameters = [
                    ['backend', 'b', '8.8.8.8', 'Test backend to use']
                    ]

class TracerouteTest(scapyt.BaseScapyTest):
    name = "Multi Protocol Traceroute Test"
    author = "Arturo Filastò"
    version = 0.1

    usageOptions = UsageOptions

    dst_ports = [22, 23, 80, 123, 443]

    def test_tcp_traceroute(self):
        def finished(packets, port):
            log.debug("Finished tcp")
            answered, unanswered = packets
            self.report['hops_'+str(port)] = [] 
            for snd, rcv in answered:
                report = {'ttl': snd.ttl, 'address': rcv.src}
                log.debug("Writing %s" % report)
                self.report['hops_'+str(port)].append(report)
            return

        dl = []
        for port in self.dst_ports:
            packets = IP(dst=self.localOptions['backend'], 
                    ttl=(4,25),id=RandShort())/TCP(flags=0x2, dport=port)
            d = self.sr(packets, timeout=2)
            d.addCallback(finished, port)
            dl.append(d)
        return defer.DeferredList(dl)

    def test_udp_traceroute(self):
        def finished(packets):
            log.debug("Finished udp")
            answered, unanswered = packets
            self.report['hops_'+str(port)].append(report)
            for snd, rcv in answered:
                report = {'ttl': snd.ttl, 'address': rcv.src}
                log.debug("Writing %s" % report)
                self.report['hops_'+str(port)].append(report)
            return

        dl = []
        for port in self.dst_ports:
            packets = IP(dst=self.localOptions['backend'],
                    ttl=(4,25),id=RandShort())/UDP(dport=port)
            d = self.sr(packets, timeout=2)
            d.addCallback(finished, port)
            dl.append(d)
        return defer.DeferredList(dl)


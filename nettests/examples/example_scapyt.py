# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.utils import log
from ooni.templates import scapyt
from scapy.all import IP, ICMP


class ExampleICMPPingScapy(scapyt.BaseScapyTest):
    name = "Example ICMP Ping Test"
    author = "Arturo Filastò"
    version = 0.1

    def test_icmp_ping(self):
        log.msg("Pinging 8.8.8.8")
        def finished(packets):
            print packets
            answered, unanswered = packets
            for snd, rcv in answered:
                rcv.show()

        packets = IP(dst='8.8.8.8')/ICMP()
        d = self.sr(packets)
        d.addCallback(finished)
        return d

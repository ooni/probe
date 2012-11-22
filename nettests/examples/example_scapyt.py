# -*- encoding: utf-8 -*-
#
# :licence: see LICENSE

from twisted.python import usage

from scapy.all import IP, ICMP

from ooni.templates import scapyt

class UsageOptions(usage.Options):
    optParameters = [['target', 't', '8.8.8.8', "Specify the target to ping"]]
    
class ExampleICMPPingScapy(scapyt.BaseScapyTest):
    name = "Example ICMP Ping Test"

    usageOptions = UsageOptions

    def test_icmp_ping(self):
        def finished(packets):
            print packets
            answered, unanswered = packets
            for snd, rcv in answered:
                rcv.show()

        packets = IP(dst=self.localOptions['target'])/ICMP()
        d = self.sr(packets)
        d.addCallback(finished)
        return d

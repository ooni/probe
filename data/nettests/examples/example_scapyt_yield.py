# -*- encoding: utf-8 -*-
#
# :licence: see LICENSE

from twisted.python import usage
from twisted.internet import defer

from scapy.all import IP, ICMP

from ooni.templates import scapyt

class UsageOptions(usage.Options):
    optParameters = [['target', 't', self.localOptions['target'], "Specify the target to ping"]]

class ExampleICMPPingScapyYield(scapyt.BaseScapyTest):
    name = "Example ICMP Ping Test"

    usageOptions = UsageOptions

    @defer.inlineCallbacks
    def test_icmp_ping(self):
        packets = IP(dst=self.localOptions['target'])/ICMP()
        answered, unanswered = yield self.sr(packets)
        for snd, rcv in answered:
            rcv.show()

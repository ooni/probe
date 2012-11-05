# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.utils import log
from ooni.templates import scapyt
from scapy.all import *

class ExampleScapy(scapyt.ScapyTest):
    name = "Example Scapy Test"
    author = "Arturo Filastò"
    version = 0.1

    inputs = [IP(dst="8.8.8.8")/TCP(dport=31337),
              IP(dst="ooni.nu")/TCP(dport=31337)]

    requiresRoot = True

    def test_sendReceive(self):
        log.msg("Running send receive")
        if self.receive:
            log.msg("Sending and receiving packets.")
            d = self.sendReceivePackets(self.buildPackets())
        else:
            log.msg("Sending packets.")
            d = self.sendPackets(self.buildPackets())

        def finished(data):
            log.msg("Finished sending")
            return data

        d.addCallback(finished)
        return

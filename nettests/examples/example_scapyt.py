# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.utils import log
from ooni.templates import scapyt
from scapy.all import IP, TCP

class ExampleBasicScapy(scapyt.BaseScapyTest):
    name = "Example Scapy Test"
    author = "Arturo Filastò"
    version = 0.1

    def test_send_raw_ip_frame(self):
        log.msg("Running send receive")
        ans, unans = self.sr(IP(dst='8.8.8.8')/TCP(), timeout=1)

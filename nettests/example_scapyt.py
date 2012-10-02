# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.templates import scapyt
from scapy.all import *
class ExampleScapy(scapyt.ScapyTest):
    name = "Example Scapy Test"
    author = "Arturo Filastò"
    version = 0.1

    inputs = [IP(dst="8.8.8.8")/TCP(dport=31337),
              IP(dst="ooni.nu")/TCP(dport=31337)]


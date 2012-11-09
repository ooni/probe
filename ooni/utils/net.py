# -*- encoding: utf-8 -*-
#
# net.py
# --------
# OONI utilities for networking related operations

import sys
from twisted.internet import threads, reactor

from scapy.all import utils

from ooni.utils import log, txscapy

def getClientAddress():
    address = {'asn': 'REPLACE_ME',
               'ip': 'REPLACE_ME'}
    return address

def capturePackets(pcap_filename):
    from scapy.all import sniff
    global stop_packet_capture
    stop_packet_capture = False

    def stopCapture():
        # XXX this is a bit of a hack to stop capturing packets when we close
        # the reactor. Ideally we would want to be able to do this
        # programmatically, but this requires some work on implementing
        # properly the sniff function with deferreds.
        global stop_packet_capture
        stop_packet_capture = True

    def writePacketToPcap(pkt):
        from scapy.all import utils
        pcapwriter = txscapy.TXPcapWriter(pcap_filename, append=True)
        pcapwriter.write(pkt)
        if stop_packet_capture:
            sys.exit(1)

    d = threads.deferToThread(sniff, lfilter=writePacketToPcap)
    reactor.addSystemEventTrigger('before', 'shutdown', stopCapture)
    return d

class PermissionsError(SystemExit):
    def __init__(self, *args, **kwargs):
        if not args and not kwargs:
            pe = "This test requires admin or root privileges to run. Exiting..."
            super(PermissionsError, self).__init__(pe, *args, **kwargs)
        else:
            super(PermissionsError, self).__init__(*args, **kwargs)

class IfaceError(SystemExit):
    def __init__(self, *args, **kwargs):
        super(IfaceError, self).__init__(*args, **kwargs)

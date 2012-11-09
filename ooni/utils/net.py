# -*- encoding: utf-8 -*-
#
# net.py
# --------
# OONI utilities for networking related operations

from scapy.all import utils
from twisted.internet import defer
from ooni.utils import log
from ooni.config import threadpool

def getClientAddress():
    address = {'asn': 'REPLACE_ME',
               'ip': 'REPLACE_ME'}
    return address

def writePacketToPcap(pkt):
    from scapy.all import utils
    log.debug("Writing to pcap file %s" % pkt)
    utils.wrpcap('/tmp/foo.pcap', pkt)

def capturePackets():
    from scapy.all import sniff
    return defer.deferToThread(sniff, writePacketToPcap, 
            lfilter=writePacketToPcap)

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

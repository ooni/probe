# -*- encoding: utf-8 -*-
#
# net.py
# --------
# OONI utilities for networking related operations

import sys
from zope.interface import implements

from twisted.internet import protocol, defer
from twisted.internet import threads, reactor
from twisted.web.iweb import IBodyProducer

from scapy.all import utils

from ooni.utils import log, txscapy

userAgents = [("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6", "Firefox 2.0, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)", "Internet Explorer 7, Windows Vista"),
              ("Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)", "Internet Explorer 7, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)", "Internet Explorer 6, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 5.0; Windows NT 5.1; .NET CLR 1.1.4322)", "Internet Explorer 5, Windows XP"),
              ("Opera/9.20 (Windows NT 6.0; U; en)", "Opera 9.2, Windows Vista"),
              ("Opera/9.00 (Windows NT 5.1; U; en)", "Opera 9.0, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.50", "Opera 8.5, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.0", "Opera 8.0, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; MSIE 5.5; Windows NT 5.1) Opera 7.02 [en]", "Opera 7.02, Windows XP"),
              ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.7.5) Gecko/20060127 Netscape/8.1", "Netscape 8.1, Windows XP")]

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

class BodyReceiver(protocol.Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.data = ""

    def dataReceived(self, bytes):
        self.data += bytes

    def connectionLost(self, reason):
        self.finished.callback(self.data)

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

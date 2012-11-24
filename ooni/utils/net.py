# -*- encoding: utf-8 -*-
#
# net.py
# --------
# OONI utilities for network infrastructure and hardware.
#
# :authors: Isis Lovecruft, Arturo Filasto
# :version: 0.0.1-pre-alpha
# :license: (c) 2012 Isis Lovecruft, Arturo Filasto
#           see attached LICENCE file

import sys

from zope.interface import implements
from twisted.internet import protocol, defer
from twisted.internet import threads, reactor
from twisted.web.iweb import IBodyProducer
from scapy.all import utils

from ooni.utils import log, txscapy

#if sys.platform.system() == 'Windows':
#    import _winreg as winreg


userAgents = [
    ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6", "Firefox 2.0, Windows XP"),
    ("Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)", "Internet Explorer 7, Windows Vista"),
    ("Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)", "Internet Explorer 7, Windows XP"),
    ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)", "Internet Explorer 6, Windows XP"),
    ("Mozilla/4.0 (compatible; MSIE 5.0; Windows NT 5.1; .NET CLR 1.1.4322)", "Internet Explorer 5, Windows XP"),
    ("Opera/9.20 (Windows NT 6.0; U; en)", "Opera 9.2, Windows Vista"),
    ("Opera/9.00 (Windows NT 5.1; U; en)", "Opera 9.0, Windows XP"),
    ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.50", "Opera 8.5, Windows XP"),
    ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.0", "Opera 8.0, Windows XP"),
    ("Mozilla/4.0 (compatible; MSIE 6.0; MSIE 5.5; Windows NT 5.1) Opera 7.02 [en]", "Opera 7.02, Windows XP"),
    ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.7.5) Gecko/20060127 Netscape/8.1", "Netscape 8.1, Windows XP")
    ]

class UnsupportedPlatform(Exception):
    """Support for this platform is not currently available."""

class IfaceError(Exception):
    """Could not find default network interface."""

class PermissionsError(SystemExit):
    """This test requires admin or root privileges to run. Exiting..."""

PLATFORMS = {'LINUX': sys.platform.startswith("linux"),
             'OPENBSD': sys.platform.startswith("openbsd"),
             'FREEBSD': sys.platform.startswith("freebsd"),
             'NETBSD': sys.platform.startswith("netbsd"),
             'DARWIN': sys.platform.startswith("darwin"),
             'SOLARIS': sys.platform.startswith("sunos"),
             'WINDOWS': sys.platform.startswith("win32")}


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

def getSystemResolver():
    """
    XXX implement a function that returns the resolver that is currently
    default on the system.
    """

def getClientPlatform(platform_name=None):
    for name, test in PLATFORMS.items():
        if not platform_name or platform_name.upper() == name:
            if test:
                return name, test

def getPosixIfaces():
    from twisted.internet.test import _posixifaces

    log.msg("Attempting to discover network interfaces...")
    ifaces = _posixifaces._interfaces()
    ifup = tryInterfaces(ifaces)
    return ifup

def getWindowsIfaces():
    from twisted.internet.test import _win32ifaces

    log.msg("Attempting to discover network interfaces...")
    ifaces = _win32ifaces._interfaces()
    ifup = tryInterfaces(ifaces)
    return ifup

def getIfaces(platform_name=None):
    client, test = getClientPlatform(platform_name)
    if client:
        if client == ('LINUX' or 'DARWIN') or client[-3:] == 'BSD':
            return getPosixIfaces()
        elif client == 'WINDOWS':
            return getWindowsIfaces()
        ## XXX fixme figure out how to get iface for Solaris
        else:
            return None
    else:
        raise UnsupportedPlatform

def checkInterfaces(ifaces=None, timeout=1):
    """
    @param ifaces:
        A dictionary in the form of ifaces['if_name'] = 'if_addr'.
    """
    try:
        from scapy.all import IP, ICMP
        from scapy.all import sr1   ## we want this check to be blocking
    except:
        log.msg(("Scapy required: www.secdev.org/projects/scapy"))

    ifup = {}
    if not ifaces:
        log.debug("checkInterfaces(): no interfaces specified!")
        return None

    for iface in ifaces:
        for ifname, ifaddr in iface:
            log.debug("checkInterfaces(): testing iface {} by pinging"
                      + " local address {}".format(ifname, ifaddr))
            try:
                pkt = IP(dst=ifaddr)/ICMP()
                ans, unans = sr(pkt, iface=ifname, timeout=5, retry=3)
            except Exception, e:
                raise PermissionsError if e.find("Errno 1") else log.err(e)
            else:
                if ans.summary():
                    log.debug("checkInterfaces(): got answer on interface %s"
                             + ":\n%s".format(ifname, ans.summary()))
                    ifup.update(ifname, ifaddr)
                else:
                    log.debug("Interface test packet was unanswered:\n%s"
                             % unans.summary())
    if len(ifup) > 0:
        log.msg("Discovered working network interfaces: %s" % ifup)
        return ifup
    else:
        raise IfaceError

def getNonLoopbackIfaces(platform_name=None):
    try:
        ifaces = getIfaces(platform_name)
    except UnsupportedPlatform, up:
        log.err(up)

    if not ifaces:
        log.msg("Unable to discover network interfaces...")
        return None
    else:
        found = [{i[0]: i[2]} for i in ifaces if i[0] != 'lo']
        log.debug("getNonLoopbackIfaces: Found non-loopback interfaces: %s"
                  % found)
        try:
            interfaces = checkInterfaces(found)
        except IfaceError, ie:
            log.err(ie)
            return None
        else:
            return interfaces


def getLocalAddress():
    default_iface = getDefaultIface()
    return default_iface.ipaddr


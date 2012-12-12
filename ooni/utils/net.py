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
import socket
from random import randint

from ipaddr import IPAddress
from zope.interface import implements
from twisted.internet import protocol, defer
from twisted.internet import threads, reactor
from twisted.web.iweb import IBodyProducer
from scapy.all import utils

from ooni.utils import log, txscapy
from ooni.utils import PermissionsError

#if sys.platform.system() == 'Windows':
#    import _winreg as winreg

PLATFORMS = {'LINUX': sys.platform.startswith("linux"),
             'OPENBSD': sys.platform.startswith("openbsd"),
             'FREEBSD': sys.platform.startswith("freebsd"),
             'NETBSD': sys.platform.startswith("netbsd"),
             'DARWIN': sys.platform.startswith("darwin"),
             'SOLARIS': sys.platform.startswith("sunos"),
             'WINDOWS': sys.platform.startswith("win32")}

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
    """
    Determines if the client's OS is Windows or Posix based, and then calls
    the appropriate function for retrieving interfaces.
    """
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

def randomFreePort(addr="127.0.0.1"):
    """
    Args:

        addr (str): the IP address to attempt to bind to.

    Returns an int representing the free port number at the moment of calling

    Note: there is no guarantee that some other application will attempt to
    bind to this port once this function has been called.
    """
    free = False
    while not free:
        port = randint(1024, 65535)
        s = socket.socket()
        try:
            s.bind((addr, port))
            free = True
        except:
            pass
        s.close()
    return port


def checkInterfaces(ifaces=None, timeout=1):
    """
    Check given network interfaces to see that they can send and receive
    packets. This is similar to :func:`getDefaultIface`, except that function
    only retrieves the name of the interface which is associated with the LAN,
    whereas this function validates tx/rx capabilities.

    @param ifaces:
        (optional) A dictionary in the form of ifaces['if_name'] = 'if_addr'.
    @param timeout:
        An integer specifying the number of seconds to timeout if
        no reply is received for our pings.
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
    """
    Get the iface names of all client network interfaces which are not
    the loopback interface, regardless of whether they route to internal
    or external networks.

    @param platform_name: (optional) The client interface, if known. Should
        be given precisely as listed in ooni.utils.net.PLATFORMS.
    @return: A list of strings of non-loopback iface names.
    """
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

def getNetworksFromRoutes():
    """
    Get the networks this client is current on from the kernel routing table.
    Each network is returned as a :class:`ipaddr.IPNetwork`, with the
    network range as the name of the network, i.e.:

        network.compressed = '127.0.0.1/32'
        network.netmask = IPv4Address('255.0.0.0')
        network.ipaddr = IPv4Address('127.0.0.1')
        network.gateway = IPv4Address('0.0.0.0')
        network.iface = 'lo'

    This is mostly useful for retrieving the default network interface in a
    portable manner, though it could be used to conduct local network checks
    for things like rogue DHCP servers, or perhaps test that the clients NAT
    router is not the mistakenly the source of a perceived censorship event.

    @return: A list of :class:`ipaddr.IPNetwork` objects with routing table
             information.
    """
    from scapy.all import conf, ltoa, read_routes
    from ipaddr    import IPNetwork, IPAddress

    conf.verb = 0     # Hide the warnings
    networks = []
    for nw, nm, gw, iface, addr in read_routes():
        n = IPNetwork( ltoa(nw) )
        (n.netmask, n.gateway, n.ipaddr) = [ IPAddress(x) for x in
                                             [nm, gw, addr] ]
        n.iface = iface
        if not n.compressed in networks:
            networks.append(n)
    return networks

def getDefaultIface():
    """
    Get the client's default network interface.

    @return: A string containing the name of the default working interface.
    @raise IfaceError: If no working interface is found.
    """
    networks = getNetworksFromRoutes()
    for net in networks:
        if net.is_private:
            return net.iface
    raise IfaceError

def getLocalAddress():
    """
    Get the rfc1918 IP address of the default working network interface.

    @return: The properly-formatted, validated, local IPv4/6 address of the
             client's default working network interface.
    """
    default_iface = getDefaultIface()
    return default_iface.ipaddr

def checkIPandPort(raw_ip, raw_port):
    """
    Check that IP and Port are a legitimate address and portnumber.

    @return: The validated ip and port, else None.
    """
    try:
        port = int(raw_port)
        assert port in xrange(1, 65535), "Port out of range."
        ip = IPAddress(raw_ip)    ## either IPv4 or IPv6
    except Exception, e:
        log.err(e)
        return
    else:
        return ip.compressed, port

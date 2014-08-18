import sys
import socket
from random import randint

from zope.interface import implements
from twisted.internet import protocol, defer
from twisted.web.iweb import IBodyProducer

from ooni.utils import log

# if sys.platform.system() == 'Windows':
# import _winreg as winreg

# These user agents are taken from the "How Unique Is Your Web Browser?"
# (https://panopticlick.eff.org/browser-uniqueness.pdf) paper as the browser user
# agents with largest anonymity set.

userAgents = ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
              "Mozilla/5.0 (iPhone; U; CPU iPhone OS 3 1 2 like Mac OS X; en-us)"
              "AppleWebKit/528.18 (KHTML, like Gecko) Mobile/7D11",
              "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6",
              "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6",
              "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6",
              "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2) Gecko/20100115 Firefox/3.6",
              "Mozilla/5.0 (Windows; U; Windows NT 6.1; de; rv:1.9.2) Gecko/20100115 Firefox/3.6",
              "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.2) Gecko/20100115 Firefox/3.6",
              "Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
              "Mozilla/5.0 (Windows; U; Windows NT 5.1; de; rv:1.9.1.7) "
              "Gecko/20091221 Firefox/3.5.7 (.NET CLR 3.5.30729)")


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
    def __init__(self, finished, content_length=None, body_processor=None):
        self.finished = finished
        self.data = ""
        self.bytes_remaining = content_length
        self.body_processor = body_processor

    def dataReceived(self, b):
        self.data += b
        if self.bytes_remaining:
            if self.bytes_remaining == 0:
                self.connectionLost(None)
            else:
                self.bytes_remaining -= len(b)

    def connectionLost(self, reason):
        try:
            if self.body_processor:
                self.data = self.body_processor(self.data)
            self.finished.callback(self.data)
        except Exception as exc:
            self.finished.errback(exc)


class Downloader(protocol.Protocol):
    def __init__(self, download_path,
                 finished, content_length=None):
        self.finished = finished
        self.bytes_remaining = content_length
        self.fp = open(download_path, 'w+')

    def dataReceived(self, b):
        self.fp.write(b)
        if self.bytes_remaining:
            if self.bytes_remaining == 0:
                self.connectionLost(None)
            else:
                self.bytes_remaining -= len(b)

    def connectionLost(self, reason):
        self.fp.flush()
        self.fp.close()
        self.finished.callback(None)


class ConnectAndCloseProtocol(protocol.Protocol):
    def connectionMade(self):
        self.transport.loseConnection()

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
    @param ifaces:
        A dictionary in the form of ifaces['if_name'] = 'if_addr'.
    """
    try:
        from scapy.all import IP, ICMP
        from scapy.all import sr1  ## we want this check to be blocking
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
                pkt = IP(dst=ifaddr) / ICMP()
                ans, unans = sr1(pkt, iface=ifname, timeout=5, retry=3)
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

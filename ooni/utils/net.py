import sys
import socket
from distutils.spawn import find_executable
from random import randint

from zope.interface import implements
from twisted.internet import protocol, defer, reactor
from twisted.web.iweb import IBodyProducer

from scapy.all import IP, ICMP, sr1, conf, ltoa, read_routes, get_if_addr, get_if_list
from ipaddr import IPNetwork, IPAddress


try:
    from twisted.internet.endpoints import connectProtocol
except ImportError:
    def connectProtocol(endpoint, protocol):
            class OneShotFactory(protocol.Factory):
                def buildProtocol(self, addr):
                    return protocol
            return endpoint.connect(OneShotFactory())

from ooni.utils import log
from ooni.errors import IfaceError, UnsupportedPlatform

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


class PingProcess(protocol.ProcessProtocol):
    def __init__(self, d):
        self.data = ''
        self.d = d

    def connectionMade(self):
        self.transport.closeStdin()

    def outReceived(self, data):
        self.data += data

    def outConnectionLost(self):
        self.transport.loseConnection()
        self.d.callback(self.data)

    def processExited(self, reason):
        self.transport.loseConnection()
        if not self.d.called:
            self.d.errback(reason)


def getClientPlatform(platform_name=None):
    for name, test in PLATFORMS.items():
        if not platform_name or platform_name.upper() == name:
            if test:
                return name


def getPosixIfaces():
    from twisted.internet.test import _posixifaces

    ifaces = _posixifaces._interfaces()
    return ifaces


def getWindowsIfaces():
    from twisted.internet.test import _win32ifaces

    ifaces = _win32ifaces._interfaces()
    return ifaces


def getIfaces(platform_name=None):
    client = getClientPlatform(platform_name)
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


@defer.inlineCallbacks
def isHostAlive(host):
    addrs = [addr.compressed for addr in getAddresses()]
    result = True
    if host not in addrs:
        def succ_cb(data):
            if 'Destination Host Unreachable' in data:
                return False
            return True

        def err_cb(reason):
            if reason.exit_code == 1:
                return False
            # We are conservative here
            return True

        d = defer.Deferred()
        d.addCallbacks(succ_cb, err_cb)
        ping_process = PingProcess(d)
        ping_path = find_executable('ping')
        reactor.spawnProcess(ping_process, ping_path, ['ping', '-t', '2', '-c', '1', host])
        result = yield d
        ping_process.transport.signalProcess('TERM')
    defer.returnValue(result)


def getNonLoopbackIfaces(platform_name=None):
    ifaces = {}
    try:
        ifaces = getIfaces(platform_name)
    except UnsupportedPlatform, up:
        log.err(up)

    if len(ifaces) == 0:
        log.msg("Unable to discover network interfaces...")
        return None

    found = [{i[0]: i[2]} for i in ifaces if i[0] != 'lo']
    return found


def getNetworksFromRoutes():
    """ Return a list of networks from the routing table """
    # # Hide the 'no routes' warnings
    conf.verb = 0

    networks = []
    for nw, nm, gw, iface, addr in read_routes():
        n = IPNetwork('%s/%s' % (ltoa(nw), ltoa(nm)))
        n.gateway = gw
        n.iface = iface
        if not n.compressed in networks:
            networks.append(n)

    return networks


def getAddresses():
    addresses = set()
    for i in get_if_list():
        try:
            addresses.add(get_if_addr(i))
        except:
            pass
    if '0.0.0.0' in addresses:
        addresses.remove('0.0.0.0')
    return [IPAddress(addr) for addr in addresses]


def getDefaultIface():
    """ Return the default interface or raise IfaceError """
    iface = conf.route.route('0.0.0.0', verbose=0)[0]
    if len(iface) > 0:
        return iface
    raise IfaceError


def hasRawSocketPermission():
    try:
        socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        return True
    except socket.error:
        return False

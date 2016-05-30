import sys
import socket
from random import randint

from zope.interface import implements
from twisted.internet import defer
from twisted.internet.protocol import Factory, Protocol
from twisted.web.iweb import IBodyProducer

from scapy.config import conf

from ooni.errors import IfaceError

# This is our own connectProtocol to avoid noisy twisted cluttering our logs
def connectProtocol(endpoint, protocol):
    class OneShotFactory(Factory):
        noisy = False
        def buildProtocol(self, addr):
            return protocol
    return endpoint.connect(OneShotFactory())

# if sys.platform.system() == 'Windows':
# import _winreg as winreg

# These user agents are taken from the "How Unique Is Your Web Browser?"
# (https://panopticlick.eff.org/browser-uniqueness.pdf) paper as the browser user
# agents with largest anonymity set.

userAgents = ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.9.1.7) Gecko/20091221 Firefox/3.5.7",
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

# These are the 25 most common server headers for the sites in the
# citizenlab global testing list.
COMMON_SERVER_HEADERS = (
    "date",
    "content-type",
    "server",
    "cache-control",
    "vary",
    "set-cookie",
    "location",
    "expires",
    "x-powered-by",
    "content-encoding",
    "last-modified",
    "accept-ranges",
    "pragma",
    "x-frame-options",
    "etag",
    "x-content-type-options",
    "age",
    "via",
    "p3p",
    "x-xss-protection",
    "content-language",
    "cf-ray",
    "strict-transport-security",
    "link",
    "x-varnish"
)

# This is used as a default for checking if we get the expected result when
# fetching URLs over some proxy.
GOOGLE_HUMANS = ('http://www.google.com/humans.txt', 'Google is built by a large')

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


class BodyReceiver(Protocol):
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


class Downloader(Protocol):
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


class ConnectAndCloseProtocol(Protocol):
    def connectionMade(self):
        self.transport.loseConnection()


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


def getDefaultIface():
    """ Return the default interface or raise IfaceError """
    iface = conf.route.route('0.0.0.0', verbose=0)[0]
    if len(iface) > 0:
        return iface
    raise IfaceError


def getAddresses():
    from scapy.all import get_if_addr, get_if_list
    from ipaddr import IPAddress

    addresses = set()
    for i in get_if_list():
        try:
            addresses.add(get_if_addr(i))
        except:
            pass
    if '0.0.0.0' in addresses:
        addresses.remove('0.0.0.0')
    return [IPAddress(addr) for addr in addresses]


def hasRawSocketPermission():
    try:
        socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        return True
    except socket.error:
        return False

# -*- encoding: utf-8 -*-
#
# :authors: Giovanni Pellerano
# :licence: see LICENSE

import struct
import itertools
from copy import copy

from zope.interface import implements
from twisted.web import client, _newclient, http_headers
from twisted.web._newclient import Request, RequestNotSent, RequestGenerationFailed, TransportProxyProducer, STATUS
from twisted.internet import protocol
from twisted.internet.protocol import ClientFactory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint, SSL4ClientEndpoint, _WrappingProtocol, _WrappingFactory
from twisted.internet import interfaces, defer
from twisted.internet.defer import Deferred, succeed, fail, maybeDeferred

from ooni.utils import log

class SOCKSError(Exception):
    def __init__(self, value):
        Exception.__init__(self)
        self.code = value

class SOCKSv5ClientProtocol(_WrappingProtocol):
    state = 0

    def __init__(self, connectedDeferred, wrappedProtocol, host, port):
        _WrappingProtocol.__init__(self, connectedDeferred, wrappedProtocol)
        self._host = host
        self._port = port
        self.ready = False

    def logPrefix(self):
        return 'SOCKSv5ClientProtocol'

    def socks_state_0(self, data):
        # error state
        self._connectedDeferred.errback(SOCKSError(0x00))
        return

    def socks_state_1(self, data):
        if data != "\x05\x00":
            self._connectedDeferred.errback(SOCKSError(0x00))
            return

        # Anonymous access allowed - let's issue connect
        self.transport.write(struct.pack("!BBBBB", 5, 1, 0, 3,
                                         len(self._host)) + 
                                         self._host +
                                         struct.pack("!H", self._port))

    def socks_state_2(self, data):
        if data[:2] != "\x05\x00":
            # Anonymous access denied

            errcode = ord(data[1])
            self._connectedDeferred.errback(SOCKSError(errcode))

            return

        self.ready = True
        self._wrappedProtocol.transport = self.transport
        self._wrappedProtocol.connectionMade()

        self._connectedDeferred.callback(self._wrappedProtocol)

    def connectionMade(self):
        # We implement only Anonymous access
        self.transport.write(struct.pack("!BB", 5, len("\x00")) + "\x00")

        self.state = self.state + 1

    def write(self, data):
        if self.ready:
            self.transport.write(data)
        else:
            self.buf.append(data)

    def dataReceived(self, data):
        if self.state != 3:
            getattr(self, 'socks_state_%s' % (self.state),
                    self.socks_state_0)(data)
            self.state = self.state + 1
        else:
            self._wrappedProtocol.dataReceived(data)

class SOCKSv5ClientFactory(_WrappingFactory):
    protocol = SOCKSv5ClientProtocol

    def __init__(self, wrappedFactory, host, port):
        _WrappingFactory.__init__(self, wrappedFactory)
        self._host, self._port = host, port

    def logPrefix(self):
        return 'SOCKSv5ClientFactory'

    def buildProtocol(self, addr):
        try:
            proto = self._wrappedFactory.buildProtocol(addr)
        except:
            self._onConnection.errback()
        else:
            return self.protocol(self._onConnection, proto,
                                 self._host, self._port)

class SOCKS5ClientEndpoint(object):
    implements(interfaces.IStreamClientEndpoint)

    def __init__(self, reactor, sockshost, socksport,
                 host, port, timeout=30, bindAddress=None):

        self._reactor = reactor
        self._sockshost = sockshost
        self._socksport = socksport
        self._host = host
        self._port = port
        self._timeout = timeout
        self._bindAddress = bindAddress

    def logPrefix(self):
        return 'SOCKSv5ClientEndpoint'

    def connect(self, protocolFactory):
        try:
            wf = SOCKSv5ClientFactory(protocolFactory, self._host, self._port)
            self._reactor.connectTCP(
                self._sockshost, self._socksport, wf,
                timeout=self._timeout, bindAddress=self._bindAddress)
            return wf._onConnection
        except:
            return defer.fail()


class TrueHeaders(http_headers.Headers):
    def __init__(self, rawHeaders=None):
        self._rawHeaders = dict()
        if rawHeaders is not None:
            for name, values in rawHeaders.iteritems():
                if type(values) is list:
                  self.setRawHeaders(name, values[:])
                elif type(values) is dict:
                  self._rawHeaders[name.lower()] = values

    def setRawHeaders(self, name, values):
        if name.lower() not in self._rawHeaders:
          self._rawHeaders[name.lower()] = dict()
        self._rawHeaders[name.lower()]['name'] = name
        self._rawHeaders[name.lower()]['values'] = values

    def getDiff(self, headers, ignore=[]):
        """

        Args:

            headers: a TrueHeaders object

            ignore: specify a list of header fields to ignore

        Returns:

            a set containing the header names that are not present in
            header_dict or not present in self.
        """
        diff = set()
        field_names = []

        headers_a = copy(self)
        headers_b = copy(headers)
        for name in ignore:
            try:
                del headers_a._rawHeaders[name.lower()]
            except KeyError:
                pass
            try:
                del headers_b._rawHeaders[name.lower()]
            except KeyError:
                pass

        for k, v in itertools.chain(headers_a.getAllRawHeaders(), \
                headers_b.getAllRawHeaders()):
            field_names.append(k)

        for name in field_names:
            if self.getRawHeaders(name) and headers.getRawHeaders(name):
                pass
            else:
                diff.add(name)
        return diff

    def getAllRawHeaders(self):
        for k, v in self._rawHeaders.iteritems():
            yield v['name'], v['values']

    def getRawHeaders(self, name, default=None):
        if name.lower() in self._rawHeaders:
            return self._rawHeaders[name.lower()]['values']
        return default

class HTTPClientParser(_newclient.HTTPClientParser):
    def logPrefix(self):
        return 'HTTPClientParser'

    def connectionMade(self):
        self.headers = TrueHeaders()
        self.connHeaders = TrueHeaders()
        self.state = STATUS
        self._partialHeader = None

    def headerReceived(self, name, value):
        if self.isConnectionControlHeader(name):
            headers = self.connHeaders
        else:
            headers = self.headers
        headers.addRawHeader(name, value)

class HTTP11ClientProtocol(_newclient.HTTP11ClientProtocol):
    def request(self, request):
        if self._state != 'QUIESCENT':
            return fail(RequestNotSent())

        self._state = 'TRANSMITTING'
        _requestDeferred = maybeDeferred(request.writeTo, self.transport)
        self._finishedRequest = Deferred()

        self._currentRequest = request

        self._transportProxy = TransportProxyProducer(self.transport)
        self._parser = HTTPClientParser(request, self._finishResponse)
        self._parser.makeConnection(self._transportProxy)
        self._responseDeferred = self._parser._responseDeferred

        def cbRequestWrotten(ignored):
            if self._state == 'TRANSMITTING':
                self._state = 'WAITING'
                self._responseDeferred.chainDeferred(self._finishedRequest)

        def ebRequestWriting(err):
            if self._state == 'TRANSMITTING':
                self._state = 'GENERATION_FAILED'
                self.transport.loseConnection()
                self._finishedRequest.errback(
                    Failure(RequestGenerationFailed([err])))
            else:
                log.err(err, 'Error writing request, but not in valid state '
                             'to finalize request: %s' % self._state)

        _requestDeferred.addCallbacks(cbRequestWrotten, ebRequestWriting)

        return self._finishedRequest

class _HTTP11ClientFactory(client._HTTP11ClientFactory):
    def buildProtocol(self, addr):
        return HTTP11ClientProtocol(self._quiescentCallback)

try:
    class HTTPConnectionPool(client.HTTPConnectionPool):
        _factory = _HTTP11ClientFactory
except AttributeError:
    log.err("Your version of Twisted is outdated and we will not support HTTPConnectionPool")
    HTTPConnectionPool = None

class UnsupportedTwistedVersion(Exception):
    pass

class Agent(client.Agent):
    def __init__(self, reactor,
                 contextFactory=client.WebClientContextFactory(),
                 connectTimeout=None, bindAddress=None,
                 pool=None, sockshost=None, socksport=None):
        if pool is None and HTTPConnectionPool:
            pool = HTTPConnectionPool(reactor, False)
        self._reactor = reactor
        self._pool = pool
        self._contextFactory = contextFactory
        self._connectTimeout = connectTimeout
        self._bindAddress = bindAddress
        self._sockshost = sockshost
        self._socksport = socksport

    def logPrefix(self):
        return 'SOCKSAgent'

    def request(self, method, uri, headers=None, bodyProducer=None):
        if (uri.startswith('shttp') or uri.startswith('httpo')) and not HTTPConnectionPool:
            log.err("Requests over SOCKS are supported only with versions of Twisted >= 12.1.0")
            raise UnsupportedTwistedVersion
        return client.Agent.request(self, method, uri, headers, bodyProducer)

    def _getEndpoint(self, scheme, host, port):
        kwargs = {}
        if self._connectTimeout is not None:
            kwargs['timeout'] = self._connectTimeout
        kwargs['bindAddress'] = self._bindAddress
        if scheme == 'http':
            return TCP4ClientEndpoint(self._reactor, host, port, **kwargs)
        elif scheme == 'shttp':
            return SOCKS5ClientEndpoint(self._reactor, self._sockshost,
                    self._socksport, host, port, **kwargs)
        elif scheme == 'httpo':
            return SOCKS5ClientEndpoint(self._reactor, self._sockshost,
                    self._socksport, host, port, **kwargs)
        elif scheme == 'https':
            return SSL4ClientEndpoint(self._reactor, host, port,
                    self._wrapContextFactory(host, port), **kwargs)
        else:
            raise SchemeNotSupported("Unsupported scheme: %r" % (scheme,))

    def _requestWithEndpoint(self, key, endpoint, method, parsedURI,
                             headers, bodyProducer, requestPath):
        if headers is None:
            headers = TrueHeaders()
        if not headers.hasHeader('host'):
            headers = headers.copy()
            headers.addRawHeader(
                'host', self._computeHostValue(parsedURI.scheme,
                    parsedURI.host, parsedURI.port))

        d = self._pool.getConnection(key, endpoint)
        def cbConnected(proto):
            return proto.request(
                Request(method, requestPath, headers, bodyProducer,
                        persistent=self._pool.persistent))
        d.addCallback(cbConnected)
        return d


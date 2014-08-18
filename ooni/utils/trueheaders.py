# :authors: Giovanni Pellerano
# :licence: see LICENSE
#
# Here we make sure that the HTTP Headers sent and received are True. By this
# we mean that they are not normalized and that the ordering is maintained.

import itertools
from copy import copy

from twisted.web import client, _newclient, http_headers
from twisted.web._newclient import RequestNotSent, RequestGenerationFailed, TransportProxyProducer, STATUS
from twisted.internet import reactor
from twisted.internet.defer import Deferred, fail, maybeDeferred, failure

from txsocksx.http import SOCKS5Agent
from txsocksx.client import SOCKS5ClientFactory

SOCKS5ClientFactory.noisy = False

from ooni.utils import log


class TrueHeaders(http_headers.Headers):
    def __init__(self, rawHeaders=None):
        self._rawHeaders = dict()
        if rawHeaders is not None:
            for name, values in rawHeaders.iteritems():
                if type(values) is list:
                    self.setRawHeaders(name, values[:])
                elif type(values) is dict:
                    self._rawHeaders[name.lower()] = values
                elif type(values) is str:
                    self.setRawHeaders(name, values)

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
                    failure.Failure(RequestGenerationFailed([err])))
            else:
                log.err(err, 'Error writing request, but not in valid state '
                             'to finalize request: %s' % self._state)

        _requestDeferred.addCallbacks(cbRequestWrotten, ebRequestWriting)

        return self._finishedRequest


class _HTTP11ClientFactory(client._HTTP11ClientFactory):
    noisy = False

    def buildProtocol(self, addr):
        return HTTP11ClientProtocol(self._quiescentCallback)


class HTTPConnectionPool(client.HTTPConnectionPool):
    _factory = _HTTP11ClientFactory


class TrueHeadersAgent(client.Agent):
    def __init__(self, *args, **kw):
        super(TrueHeadersAgent, self).__init__(*args, **kw)
        self._pool = HTTPConnectionPool(reactor, False)


class TrueHeadersSOCKS5Agent(SOCKS5Agent):
    def __init__(self, *args, **kw):
        super(TrueHeadersSOCKS5Agent, self).__init__(*args, **kw)
        self._pool = HTTPConnectionPool(reactor, False)

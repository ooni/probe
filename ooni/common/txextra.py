import itertools
from copy import copy

from twisted.web.http_headers import Headers
from twisted.web import error

from twisted.web.client import BrowserLikeRedirectAgent
from twisted.web._newclient import ResponseFailed
from twisted.web._newclient import HTTPClientParser, ParseError
from twisted.python.failure import Failure

from twisted.web import client, _newclient

from twisted.web._newclient import RequestNotSent, RequestGenerationFailed
from twisted.web._newclient import TransportProxyProducer, STATUS

from twisted.internet import reactor
from twisted.internet.defer import Deferred, fail, maybeDeferred, failure

from twisted.python import log

class TrueHeaders(Headers):
    def __init__(self, rawHeaders=None):
        self._rawHeaders = dict()
        if rawHeaders is not None:
            for name, values in rawHeaders.iteritems():
                if type(values) is list:
                    self.setRawHeaders(name, values[:])
                elif type(values) is str:
                    self.setRawHeaders(name, values)

    def setRawHeaders(self, name, values):
        if name.lower() not in self._rawHeaders:
            self._rawHeaders[name.lower()] = dict()
        self._rawHeaders[name.lower()]['name'] = name
        self._rawHeaders[name.lower()]['values'] = values

    def getAllRawHeaders(self):
        for _, v in self._rawHeaders.iteritems():
            yield v['name'], v['values']

    def getRawHeaders(self, name, default=None):
        if name.lower() in self._rawHeaders:
            return self._rawHeaders[name.lower()]['values']
        return default


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

        for k, v in itertools.chain(headers_a.getAllRawHeaders(),
                                    headers_b.getAllRawHeaders()):
            field_names.append(k)

        for name in field_names:
            if self.getRawHeaders(name) and headers.getRawHeaders(name):
                pass
            else:
                diff.add(name)
        return list(diff)

class HTTPClientParser(_newclient.HTTPClientParser):
    def logPrefix(self):
        return 'HTTPClientParser'

    def connectionMade(self):
        self.headers = TrueHeaders()
        self.connHeaders = TrueHeaders()
        self.state = STATUS
        self._partialHeader = None

    def headerReceived(self, name, value):
        if self.isConnectionControlHeader(name.lower()):
            headers = self.connHeaders
        else:
            headers = self.headers
        headers.addRawHeader(name, value)

    def statusReceived(self, status):
        # This is a fix for invalid number of parts
        try:
            return _newclient.HTTPClientParser.statusReceived(self, status)
        except ParseError as exc:
            if exc.args[0] == 'wrong number of parts':
                return _newclient.HTTPClientParser.statusReceived(self,
                                                                  status + " XXX")
            raise

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

class FixedRedirectAgent(BrowserLikeRedirectAgent):
    """
    This is a redirect agent with this patch manually applied:
    https://twistedmatrix.com/trac/ticket/8265
    """
    def _handleRedirect(self, response, method, uri, headers, redirectCount):
        """
        Handle a redirect response, checking the number of redirects already
        followed, and extracting the location header fields.

        This is patched to fix a bug in infinite redirect loop.
        """
        if redirectCount >= self._redirectLimit:
            err = error.InfiniteRedirection(
                response.code,
                b'Infinite redirection detected',
                location=uri)
            raise ResponseFailed([Failure(err)], response)
        locationHeaders = response.headers.getRawHeaders(b'location', [])
        if not locationHeaders:
            err = error.RedirectWithNoLocation(
                response.code, b'No location header field', uri)
            raise ResponseFailed([Failure(err)], response)
        location = self._resolveLocation(
            # This is the fix to properly handle redirects
            response.request.absoluteURI,
            locationHeaders[0]
        )
        deferred = self._agent.request(method, location, headers)

        def _chainResponse(newResponse):
            newResponse.setPreviousResponse(response)
            return newResponse

        deferred.addCallback(_chainResponse)
        return deferred.addCallback(
            self._handleResponse, method, uri, headers, redirectCount + 1)

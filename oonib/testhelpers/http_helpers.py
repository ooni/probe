import json
import random
import string

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.protocols import basic
from twisted.web import resource, server, static, http
from twisted.web.microdom import escape

from cyclone.web import RequestHandler, Application

from twisted.protocols import policies, basic
from twisted.web.http import Request

class SimpleHTTPChannel(basic.LineReceiver, policies.TimeoutMixin):
    """
    This is a simplified version of twisted.web.http.HTTPChannel to overcome
    header lowercase normalization. It does not actually implement the HTTP
    protocol, but only the subset of it that we need for testing.

    What this HTTP channel currently does is process the HTTP Request Line and
    the Request Headers and returns them in a JSON datastructure in the order
    we received them.

    The returned JSON dict looks like so:

    {
        'request_headers': 
            [['User-Agent', 'IE6'], ['Content-Length', 200]]
        'request_line':
            'GET / HTTP/1.1'
    }
    """
    requestFactory = Request
    __first_line = 1
    __header = ''
    __content = None

    length = 0
    maxHeaders = 500
    requestLine = ''
    headers = []

    timeOut = 60 * 60 * 12

    def __init__(self):
        self.requests = []

    def connectionMade(self):
        self.setTimeout(self.timeOut)

    def lineReceived(self, line):
        if self.__first_line:
            self.requestLine = line
            self.__first_line = 0
        elif line == '':
            # We have reached the end of the headers.
            if self.__header:
                self.headerReceived(self.__header)
            self.__header = ''
            self.allHeadersReceived()
            self.setRawMode()
        elif line[0] in ' \t':
            # This is to support header field value folding over multiple lines
            # as specified by rfc2616.
            self.__header = self.__header+'\n'+line
        else:
            if self.__header:
                self.headerReceived(self.__header)
            self.__header = line

    def headerReceived(self, line):
        header, data = line.split(':', 1)
        self.headers.append((header, data.strip()))

    def allHeadersReceived(self):
        headers_dict = {}
        for k, v in self.headers:
            headers_dict[k] = v
        response = {'request_headers': self.headers,
            'request_line': self.requestLine,
            'headers_dict': headers_dict
        }
        self.transport.write('HTTP/1.1 200 OK\r\n\r\n')
        self.transport.write(json.dumps(response))
        self.transport.loseConnection()


class HTTPReturnJSONHeadersHelper(protocol.ServerFactory):
    protocol = SimpleHTTPChannel
    def buildProtocol(self, addr):
        p = self.protocol()
        p.headers = []
        return p

class HTTPTrapAll(RequestHandler):
    def _execute(self, transforms, *args, **kwargs):
        self._transforms = transforms
        defer.maybeDeferred(self.prepare).addCallbacks(
                    self._execute_handler,
                    lambda f: self._handle_request_exception(f.value),
                    callbackArgs=(args, kwargs))

    def _execute_handler(self, r, args, kwargs):
        if not self._finished:
            args = [self.decode_argument(arg) for arg in args]
            kwargs = dict((k, self.decode_argument(v, name=k))
                            for (k, v) in kwargs.iteritems())
            # This is where we do the patching
            # XXX this is somewhat hackish
            d = defer.maybeDeferred(self.all, *args, **kwargs)
            d.addCallbacks(self._execute_success, self._execute_failure)
            self.notifyFinish().addCallback(self.on_connection_close)


class HTTPRandomPage(HTTPTrapAll):
    """
    This generates a random page of arbitrary length and containing the string
    selected by the user.
    /<length>/<keyword>
    XXX this is currently disabled as it is not of use to any test.
    """
    isLeaf = True
    def _gen_random_string(self, length):
        return ''.join(random.choice(string.letters) for x in range(length))

    def genRandomPage(self, length=100, keyword=None):
        data = self._gen_random_string(length/2)
        if keyword:
            data += keyword
        data += self._gen_random_string(length - length/2)
        data += '\n'
        return data

    def all(self, length, keyword):
        length = 100
        if length > 100000:
            length = 100000
        return self.genRandomPage(length, keyword)

HTTPRandomPageHelper = Application([
    # XXX add regexps here
    (r"/(.*)/(.*)", HTTPRandomPage)
])


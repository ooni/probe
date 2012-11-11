import json
import random
import string

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.protocols import basic
from twisted.web import resource, server, static, http
from twisted.web.microdom import escape

from cyclone.web import RequestHandler, Application

class HTTPTrapAll(RequestHandler):
    """
    Master class to be used to trap all the HTTP methods and make capitalized
    requests pass.
    """
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

class HTTPReturnJSONHeaders(HTTPTrapAll):
    def all(self):
        # XXX make sure that the request headers are in the correct order
        submitted_data = {'request_body': self.request.body,
                'request_headers': self.request.headers,
                'request_uri': self.request.uri,
                'request_method': self.request.method}
        response = json.dumps(submitted_data)
        self.write(response)

HTTPReturnJSONHeadersHelper = Application([
    (r"/*", HTTPReturnJSONHeaders)
])


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


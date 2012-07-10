import random
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.utils import log

useragents = [("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6", "Firefox 2.0, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)", "Internet Explorer 7, Windows Vista"),
              ("Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)", "Internet Explorer 7, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; .NET CLR 1.1.4322)", "Internet Explorer 6, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 5.0; Windows NT 5.1; .NET CLR 1.1.4322)", "Internet Explorer 5, Windows XP"),
              ("Opera/9.20 (Windows NT 6.0; U; en)", "Opera 9.2, Windows Vista"),
              ("Opera/9.00 (Windows NT 5.1; U; en)", "Opera 9.0, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.50", "Opera 8.5, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; en) Opera 8.0", "Opera 8.0, Windows XP"),
              ("Mozilla/4.0 (compatible; MSIE 6.0; MSIE 5.5; Windows NT 5.1) Opera 7.02 [en]", "Opera 7.02, Windows XP"),
              ("Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.7.5) Gecko/20060127 Netscape/8.1", "Netscape 8.1, Windows XP")]

class BodyReceiver(protocol.Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.data = ""

    def dataReceived(self, bytes):
        self.data += bytes

    def connectionLost(self, reason):
        self.finished.callback(self.data)

from twisted.web.http_headers import Headers
class HTTPTest(OONITest):
    """
    A utility class for dealing with HTTP based testing. It provides methods to
    be overriden for dealing with HTTP based testing.
    The main functions to look at are processResponseBody and
    processResponseHeader that are invoked once the headers have been received
    and once the request body has been received.
    """
    randomize_ua = True

    def initialize(self):
        from twisted.web.client import Agent
        import yaml

        self.agent = Agent(self.reactor)
        self.request = {}
        self.response = {}

    def _processResponseBody(self, data):
        self.response['body'] = data
        self.result['response'] = self.response
        self.processResponseBody(data)

    def processResponseBody(self, data):
        """
        This should handle all the response body smushing for getting it ready
        to be passed onto the control.

        @param data: The content of the body returned.
        """
        pass

    def processResponseHeaders(self, headers):
        """
        This should take care of dealing with the returned HTTP headers.

        @param headers: The content of the returned headers.
        """
        pass

    def experiment(self, args):
        log.msg("Running experiment")
        url = self.local_options['url'] if 'url' not in args else args['url']

        d = self.build_request(url)
        def finished(data):
            return data

        d.addCallback(self._cbResponse)
        d.addCallback(finished)
        return d

    def _cbResponse(self, response):
        self.response['headers'] = list(response.headers.getAllRawHeaders())
        self.processResponseHeaders(self.response['headers'])
        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished))
        finished.addCallback(self._processResponseBody)

    def randomize_useragent(self):
        user_agent = random.choice(useragents)
        self.request['headers']['User-Agent'] = [user_agent]

    def build_request(self, url, method="GET", headers=None, body=None):
        self.request['method'] = method
        self.request['url'] = url
        self.request['headers'] = headers if headers else {}
        self.request['body'] = body
        if self.randomize_ua:
            self.randomize_useragent()

        self.result['request'] = self.request
        return self.agent.request(self.request['method'], self.request['url'],
                                  Headers(self.request['headers']),
                                  self.request['body'])

    def load_assets(self):
        if self.local_options:
            return {'url': Asset(self.local_options['asset'])}
        else:
            return {}


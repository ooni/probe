# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer
from twisted.internet.ssl import ClientContextFactory

from twisted.web.http_headers import Headers

from ooni.nettest import TestCase
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


class WebClientContextFactory(ClientContextFactory):
    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)

class BodyReceiver(protocol.Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.data = ""

    def dataReceived(self, bytes):
        self.data += bytes

    def connectionLost(self, reason):
        self.finished.callback(self.data)

class HTTPTest(TestCase):
    """
    A utility class for dealing with HTTP based testing. It provides methods to
    be overriden for dealing with HTTP based testing.
    The main functions to look at are processResponseBody and
    processResponseHeader that are invoked once the headers have been received
    and once the request body has been received.
    """
    name = "HTTP Test"
    version = 0.1

    randomizeUA = True
    followRedirects = False

    def setUp(self):
        try:
            import OpenSSL
        except:
            log.err("Warning! pyOpenSSL is not installed. https websites will"
                     "not work")
        from twisted.web.client import Agent
        from twisted.internet import reactor

        self.agent = Agent(reactor)

        if self.followRedirects:
            from twisted.web.client import RedirectAgent
            self.agent = RedirectAgent(self.agent)
        self.request = {}
        self.response = {}

    def _processResponseBody(self, data):
        self.response['body'] = data
        self.report['response'] = self.response

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

    def processRedirect(self, location):
        """
        Handle a redirection via a 3XX HTTP status code.

        @param location: the url that is being redirected to.
        """
        pass

    def doRequest(self, url, method="GET", headers=None, body=None):
        try:
            d = self.build_request(url, method, headers, body)
        except Exception, e:
            print e
            self.report['error'] = e

        def errback(data):
            print data
            #self.report["error"] = data

        def finished(data):
            return

        d.addErrback(errback)
        d.addCallback(self._cbResponse)
        d.addCallback(finished)
        return d

    def _cbResponse(self, response):
        self.response['headers'] = response.headers
        self.response['code'] = response.code
        self.response['length'] = response.length
        self.response['version'] = response.length

        if str(self.response['code']).startswith('3'):
            self.processRedirect(response.headers.getRawHeaders('Location')[0])

        self.processResponseHeaders(self.response['headers'])

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished))
        finished.addCallback(self._processResponseBody)

        return finished

    def randomize_useragent(self):
        user_agent = random.choice(useragents)
        self.request['headers']['User-Agent'] = [user_agent]

    def build_request(self, url, method="GET", headers=None, body=None):
        self.request['method'] = method
        self.request['url'] = url
        self.request['headers'] = headers if headers else {}
        self.request['body'] = body
        if self.randomizeUA:
            self.randomize_useragent()

        self.report['request'] = self.request
        self.report['url'] = url
        req = self.agent.request(self.request['method'], self.request['url'],
                                  Headers(self.request['headers']),
                                  self.request['body'])
        return req


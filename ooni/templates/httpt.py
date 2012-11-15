# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE
import copy
import random
import struct

from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer
from twisted.internet.ssl import ClientContextFactory

from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError

from twisted.web._newclient import Request
from twisted.web.http_headers import Headers
from ooni.nettest import NetTestCase
from ooni.utils import log

from ooni.utils.net import BodyReceiver, StringProducer, userAgents

from ooni.lib.txagentwithsocks import Agent, SOCKSError

class HTTPTest(NetTestCase):
    """
    A utility class for dealing with HTTP based testing. It provides methods to
    be overriden for dealing with HTTP based testing.
    The main functions to look at are processResponseBody and
    processResponseHeader that are invoked once the headers have been received
    and once the request body has been received.

    XXX all of this requires some refactoring.
    """
    name = "HTTP Test"
    version = "0.1.1"

    randomizeUA = True
    followRedirects = False

    def _setUp(self):
        log.debug("Setting up HTTPTest")
        try:
            import OpenSSL
        except:
            log.err("Warning! pyOpenSSL is not installed. https websites will"
                     "not work")

        self.agent = Agent(reactor, sockhost="127.0.0.1", sockport=9050)

        if self.followRedirects:
            try:
                from twisted.web.client import RedirectAgent
                self.agent = RedirectAgent(self.agent)
            except:
                log.err("Warning! You are running an old version of twisted"\
                        "(<= 10.1). I will not be able to follow redirects."\
                        "This may make the testing less precise.")
                self.report['errors'].append("Could not import RedirectAgent")

        self.request = {}
        self.response = {}
        self.processInputs()
        log.debug("Finished test setup")

    def processInputs(self):
        pass

    def _processResponseBody(self, data, body_processor):
        log.debug("Processing response body")
        self.response['body'] = data
        self.report['response'] = self.response

        if body_processor:
            body_processor(data)
        else:
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

    def doRequest(self, url, method="GET",
                  headers=None, body=None, headers_processor=None,
                  body_processor=None):
        """
        Perform an HTTP request with the specified method.

        url: the full url path of the request

        method: the HTTP Method to be used

        headers: the request headers to be sent as a dict

        body: the request body

        headers_processor: a function to be used for processing the HTTP header
                          responses (defaults to self.processResponseHeaders).
                          This function takes as argument the HTTP headers as a
                          dict.

        body_processory: a function to be used for processing the HTTP response
                         body (defaults to self.processResponseBody).
                         This function takes the response body as an argument.

        """
        log.debug("Performing request %s %s %s" % (url, method, headers))

        d = self.build_request(url, method, headers, body)

        def errback(failure):
            failure.trap(ConnectionRefusedError, SOCKSError)
            if type(failure.value) is ConnectionRefusedError:
                log.err("Connection refused. The backend may be down")
            else:
                 log.err("Sock error. The SOCK proxy may be down")
            self.report["failure"] = str(failure.value)

        def finished(data):
            return

        d.addErrback(errback)
        d.addCallback(self._cbResponse, headers_processor, body_processor)
        d.addCallback(finished)
        return d

    def build_request(self, url, method="GET", 
            headers=None, body=None):
        self.request['method'] = method
        self.request['url'] = url
        self.request['headers'] = headers if headers else {}
        self.request['body'] = body

        if self.randomizeUA:
            self.randomize_useragent()

        self.report['request'] = self.request
        self.report['url'] = url

        # If we have a request body payload, set the request body to such
        # content
        if body:
            body_producer = StringProducer(self.request['body'])
        else:
            body_producer = None

        headers = Headers(self.request['headers'])

        req = self.agent.request(self.request['method'], self.request['url'],
                                  headers, body_producer)
        return req

    def _cbResponse(self, response, headers_processor, body_processor):
        log.debug("Got response %s" % response)
        if not response:
            self.report['response'] = None
            log.err("We got an empty response")
            return

        self.response['headers'] = list(response.headers.getAllRawHeaders())
        self.response['code'] = response.code
        self.response['length'] = response.length
        self.response['version'] = response.length

        if str(self.response['code']).startswith('3'):
            self.processRedirect(response.headers.getRawHeaders('Location')[0])

        if headers_processor:
            headers_processor(self.response['headers'])
        else:
            self.processResponseHeaders(self.response['headers'])

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished))
        finished.addCallback(self._processResponseBody, 
                body_processor)

        return finished

    def randomize_useragent(self):
        user_agent = random.choice(userAgents)
        self.request['headers']['User-Agent'] = [user_agent]



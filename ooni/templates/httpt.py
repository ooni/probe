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

from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni import config

from ooni.utils.net import BodyReceiver, StringProducer, userAgents

from ooni.utils.txagentwithsocks import Agent, SOCKSError, TrueHeaders

class HTTPTest(NetTestCase):
    """
    A utility class for dealing with HTTP based testing. It provides methods to
    be overriden for dealing with HTTP based testing.
    The main functions to look at are processResponseBody and
    processResponseHeader that are invoked once the headers have been received
    and once the request body has been received.

    To perform requests over Tor you will have to use the special URL schema
    "shttp". For example to request / on example.com you will have to do
    specify as URL "shttp://example.com/".

    XXX all of this requires some refactoring.
    """
    name = "HTTP Test"
    version = "0.1.1"

    randomizeUA = True
    followRedirects = False

    baseParameters = [['socksproxy', 's', None,
        'Specify a socks proxy to use for requests (ip:port)']]

    request = {}
    response = {}

    def _setUp(self):
        log.debug("Setting up HTTPTest")
        try:
            import OpenSSL
        except:
            log.err("Warning! pyOpenSSL is not installed. https websites will"
                     "not work")

        self.control_agent = Agent(reactor, sockshost="127.0.0.1",
                socksport=config.advanced.tor_socksport)

        sockshost, socksport = (None, None)
        if self.localOptions['socksproxy']:
            self.report['socksproxy'] = self.localOptions['socksproxy']
            sockshost, socksport = self.localOptions['socksproxy'].split(':')
            socksport = int(socksport)

        self.agent = Agent(reactor, sockshost=sockshost,
                socksport=socksport)

        if self.followRedirects:
            try:
                from twisted.web.client import RedirectAgent
                self.control_agent = RedirectAgent(self.control_agent)
                self.agent = RedirectAgent(self.agent)
            except:
                log.err("Warning! You are running an old version of twisted"\
                        "(<= 10.1). I will not be able to follow redirects."\
                        "This may make the testing less precise.")
                self.report['errors'].append("Could not import RedirectAgent")

        self.processInputs()
        log.debug("Finished test setup")

    def processInputs(self):
        pass

    def _processResponseBody(self, response_body, request, response, body_processor):
        log.debug("Processing response body")
        self.report['requests'].append({
            'request': {
                'headers': request['headers'],
                'body': request['body'],
                'url': request['url'],
                'method': request['method']
            },
            'response': {
                'headers': list(response.headers.getAllRawHeaders()),
                'body': response_body,
                'code': response.code
            }
        })
        if body_processor:
            body_processor(response_body)
        else:
            self.processResponseBody(response_body)

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
                  headers={}, body=None, headers_processor=None,
                  body_processor=None, use_tor=False):
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

        # We prefix the URL with 's' to make the connection go over the
        # configured socks proxy
        if use_tor:
            log.debug("Using control agent for the request")
            url = 's'+url
            agent = self.control_agent
        else:
            agent = self.agent

        if self.localOptions['socksproxy']:
            log.debug("Using SOCKS proxy %s for request" % (self.localOptions['socksproxy']))
            url = 's'+url

        log.debug("Performing request %s %s %s" % (url, method, headers))

        request = {}
        request['method'] = method
        request['url'] = url
        request['headers'] = headers
        request['body'] = body

        if self.randomizeUA:
            log.debug("Randomizing user agent")
            self.randomize_useragent(request)

        log.debug("Writing to report the request")

        if 'requests' not in self.report:
            self.report['requests'] = []

        # If we have a request body payload, set the request body to such
        # content
        if body:
            body_producer = StringProducer(request['body'])
        else:
            body_producer = None

        headers = TrueHeaders(request['headers'])

        def errback(failure):
            failure.trap(ConnectionRefusedError, SOCKSError)
            if type(failure.value) is ConnectionRefusedError:
                log.err("Connection refused. The backend may be down")
            else:
                 log.err("Sock error. The SOCK proxy may be down")
            self.report["failure"] = str(failure.value)

        def finished(data):
            return

        d = agent.request(request['method'], request['url'], headers,
                body_producer)

        d.addErrback(errback)
        d.addCallback(self._cbResponse, request, headers_processor, body_processor)
        d.addCallback(finished)
        return d

    def _cbResponse(self, response, request, headers_processor,
            body_processor):

        if not response:
            log.err("Got no response")
            return
        else:
            log.debug("Got response %s" % response)

        if str(response.code).startswith('3'):
            self.processRedirect(response.headers.getRawHeaders('Location')[0])

        # [!] We are passing to the headers_processor the headers dict and
        # not the Headers() object
        response_headers_dict = list(response.headers.getAllRawHeaders())
        if headers_processor:
            headers_processor(response_headers_dict)
        else:
            self.processResponseHeaders(response_headers_dict)

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished))
        finished.addCallback(self._processResponseBody, request,
                response, body_processor)

        return finished

    def randomize_useragent(self, request):
        user_agent = random.choice(userAgents)
        request['headers']['User-Agent'] = [user_agent]


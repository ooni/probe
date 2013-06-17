import copy
import random
import struct

from twisted.plugin import IPlugin
from twisted.internet import protocol, defer
from twisted.internet.ssl import ClientContextFactory

from twisted.internet import reactor
from twisted.internet.error import ConnectionRefusedError, DNSLookupError, TCPTimedOutError

from twisted.web._newclient import Request, Response, ResponseNeverReceived

from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni.settings import config

from ooni.utils.net import BodyReceiver, StringProducer, userAgents

from ooni.utils.txagentwithsocks import Agent, TrueHeaders
from ooni.errors import handleAllFailures


class InvalidSocksProxyOption(Exception):
    pass

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

    randomizeUA = False
    followRedirects = False

    baseParameters = [['socksproxy', 's', None,
        'Specify a socks proxy to use for requests (ip:port)']]

    request = {}
    response = {}

    requests = []
    responses = []

    def _setUp(self):
        super(HTTPTest, self)._setUp()

        try:
            import OpenSSL
        except:
            log.err("Warning! pyOpenSSL is not installed. https websites will "
                     "not work")

        self.control_agent = Agent(reactor, sockshost="127.0.0.1",
                socksport=config.tor.socks_port)

        self.report['socksproxy'] = None
        sockshost, socksport = (None, None)
        if self.localOptions['socksproxy']:
            try:
                sockshost, socksport = self.localOptions['socksproxy'].split(':')
                self.report['socksproxy'] = self.localOptions['socksproxy']
            except ValueError:
                raise InvalidSocksProxyOption
            socksport = int(socksport)

        self.agent = Agent(reactor, sockshost=sockshost, socksport=socksport)

        self.report['agent'] = 'agent'

        if self.followRedirects:
            try:
                from twisted.web.client import RedirectAgent
                self.control_agent = RedirectAgent(self.control_agent)
                self.agent = RedirectAgent(self.agent)
                self.report['agent'] = 'redirect'
            except:
                log.err("Warning! You are running an old version of twisted"\
                        "(<= 10.1). I will not be able to follow redirects."\
                        "This may make the testing less precise.")

        self.processInputs()
        log.debug("Finished test setup")

    def randomize_useragent(self, request):
        user_agent = random.choice(userAgents)
        request['headers']['User-Agent'] = [user_agent]

    def processInputs(self):
        pass

    def addToReport(self, request, response=None, response_body=None, failure_string=None):
        """
        Adds to the report the specified request and response.

        Args:
            request (dict): A dict describing the request that was made

            response (instance): An instance of
                :class:twisted.web.client.Response.
                Note: headers is our modified True Headers version.

            failure (instance): An instance of :class:twisted.internet.failure.Failure
        """
        log.debug("Adding %s to report" % request)
        request_headers = TrueHeaders(request['headers'])
        request_response = {
            'request': {
                'headers': list(request_headers.getAllRawHeaders()),
                'body': request['body'],
                'url': request['url'],
                'method': request['method']
            }
        }
        if response:
            request_response['response'] = {
                'headers': list(response.headers.getAllRawHeaders()),
                'body': response_body,
                'code': response.code
        }
        if failure_string:
            request_response['failure'] = failure_string

        self.report['requests'].append(request_response)

    def _processResponseBody(self, response_body, request, response, body_processor):
        log.debug("Processing response body")
        HTTPTest.addToReport(self, request, response, response_body)
        if body_processor:
            body_processor(response_body)
        else:
            self.processResponseBody(response_body)
        response.body = response_body
        return response

    def processResponseBody(self, body):
        """
        Overwrite this method if you wish to interact with the response body of
        every request that is made.

        Args:

            body (str): The body of the HTTP response
        """
        pass

    def processResponseHeaders(self, headers):
        """
        This should take care of dealing with the returned HTTP headers.

        Args:

            headers (dict): The returned header fields.
        """
        pass

    def processRedirect(self, location):
        """
        Handle a redirection via a 3XX HTTP status code.

        Here you may place logic that evaluates the destination that you are
        being redirected to. Matches against known censor redirects, etc.

        Note: if self.followRedirects is set to True, then this method will
            never be called.
            XXX perhaps we may want to hook _handleResponse in RedirectAgent to
            call processRedirect every time we get redirected.

        Args:

            location (str): the url that we are being redirected to.
        """
        pass

    def _cbResponse(self, response, request,
            headers_processor, body_processor):
        """
        This callback is fired once we have gotten a response for our request.
        If we are using a RedirectAgent then this will fire once we have
        reached the end of the redirect chain.

        Args:

            response (:twisted.web.iweb.IResponse:): a provider for getting our response

            request (dict): the dict containing our response (XXX this should be dropped)

            header_processor (func): a function to be called with argument a
                dict containing the response headers. This will lead
                self.headerProcessor to not be called.

            body_processor (func): a function to be called with as argument the
                body of the response. This will lead self.bodyProcessor to not
                be called.

        """
        if not response:
            log.err("Got no response for request %s" % request)
            HTTPTest.addToReport(self, request, response)
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

        try:
            content_length = response.headers.getRawHeaders('content-length')
        except IndexError:
            content_length = None

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished, content_length))
        finished.addCallback(self._processResponseBody, request,
                response, body_processor)
        return finished

    def doRequest(self, url, method="GET",
                  headers={}, body=None, headers_processor=None,
                  body_processor=None, use_tor=False):
        """
        Perform an HTTP request with the specified method and headers.

        Args:

            url (str): the full URL of the request. The scheme may be either
                http, https, or httpo for http over Tor Hidden Service.

        Kwargs:

            method (str): the HTTP method name to use for the request

            headers (dict): the request headers to send

            body (str): the request body

            headers_processor : a function to be used for processing the HTTP
                header responses (defaults to self.processResponseHeaders).
                This function takes as argument the HTTP headers as a dict.

            body_processory: a function to be used for processing the HTTP
                response body (defaults to self.processResponseBody). This
                function takes the response body as an argument.

            use_tor (bool): specify if the HTTP request should be done over Tor
                or not.

        """

        # We prefix the URL with 's' to make the connection go over the
        # configured socks proxy
        if use_tor:
            log.debug("Using Tor for the request to %s" % url)
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

        if 'requests' not in self.report:
            self.report['requests'] = []

        # If we have a request body payload, set the request body to such
        # content
        if body:
            body_producer = StringProducer(request['body'])
        else:
            body_producer = None

        headers = TrueHeaders(request['headers'])

        def errback(failure, request):
            failure_string = handleAllFailures(failure)
            log.err("Error performing %s" % request)
            HTTPTest.addToReport(self, request, failure_string=failure_string)
            return failure

        d = agent.request(request['method'], request['url'], headers,
                body_producer)

        d.addCallback(self._cbResponse, request, headers_processor,
                body_processor)
        d.addErrback(errback, request)
        return d


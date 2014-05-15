from twisted.internet import reactor, defer
from twisted.web.client import SchemeNotSupported, RedirectAgent
from txsocksx.tls import TLSWrapClientEndpoint

from ooni.settings import config
from ooni.templates.tort import TorTest
from ooni.templates.httpt import HTTPTest
from ooni.utils.trueheaders import TrueHeadersAgent, TrueHeaders
from ooni.utils.net import userAgents
from ooni.errors import handleAllFailures

class TorHTTPRequests(TorTest, HTTPTest):
    name = "Tor HTTP Requests Test"
    version = "0.1"
    description = "Fetches a list of URLs over each exit"

    inputFile = ['file', 'f', None,
            'List of URLS to perform GET requests to']
    requiredOptions = ['file']

    @defer.inlineCallbacks
    def setUp(self): 
        # XXX review these values
        d = yield self.state.protocol.set_conf(
                "UseEntryGuards", "0",
                "MaxClientCircuitsPending", "200",
                "SocksTimeout", "30",
                "CircuitIdleTimeout", "60")

    def getInputProcessor(self):
        #XXX: doesn't seem that we have any of the exitpolicy available :\
        #XXX: so the circuit might fail if port 80 isn't allowed
        if self.inputFileSpecified:
            self.inputFilename = self.localOptions[self.inputFile[0]]
            urls = open(self.inputFilename)
            exits = filter(lambda router: 'exit' in router.flags,
                            config.tor_state.routers.values())
            hexes = [exit.id_hex for exit in exits]
            for curse in hexes:
                for url in urls:
                    yield (curse, url.strip())      
                urls.seek(0)

    def test_get(self):

        exit_hex, url = self.input
        try:
            exit = self.state.routers[exit_hex]
        except KeyError:
            # Router not in consensus, sorry
            self.report['failure'] = "Router %s not in consensus." % self.input
            return

        if 'requests' not in self.report:
            self.report['requests'] = []

        request = {'method': "GET", 'url': url,
                'headers': {'User-Agent':[
                    "Mozilla/5.0 (Windows NT 6.1; rv:17.0) Gecko/20100101 Firefox/17.0"
                    ]}, 'body': None}
        headers = TrueHeaders(request['headers'])

        parent = self
        class OnionRoutedTrueHeadersAgent(TrueHeadersAgent):
            _tlsWrapper = TLSWrapClientEndpoint
            def _getEndpoint(self, scheme, host, port):
                if scheme not in ('http', 'https'):
                    raise SchemeNotSupported('unsupported scheme', scheme)
                endpoint = parent.getExitSpecificEndpoint((host,port), exit)
                if scheme == 'https':
                    endpoint = self._tlsWrapper(
                        self._wrapContextFactory(host, port), endpoint)
                return endpoint

        # follow redirects
        agent = RedirectAgent(OnionRoutedTrueHeadersAgent(reactor))
        d = agent.request("GET", url, headers=headers)

        def errback(failure, request):
            failure_string =  handleAllFailures(failure)
            self.addToReport(request, failure_string=failure_string)
            return failure

        d.addErrback(errback, request)

        headers_processor = body_processor = None
        d.addCallback(self._cbResponse, request, headers_processor, body_processor)
        return d

from twisted.internet import reactor, defer
from twisted.internet.protocol import ClientFactory, Protocol, connectionDone
from twisted.internet.ssl import ClientContextFactory, DefaultOpenSSLContextFactory
from ooni.settings import config
from ooni.templates.tort import TorTest
from ooni.utils import log, tor
from ooni import errors

from txsocksx.tls import TLSWrapClientEndpoint

from twisted.protocols import tls
from twisted.internet import interfaces
from zope.interface import implementer

from OpenSSL import crypto


@implementer(interfaces.IStreamClientEndpoint)
class haxendpoint(TLSWrapClientEndpoint):
    def _unwrapProtocol(self, proto):
        #XXX: is there any sane way to get a reference to the OpenSSL object?
        proto.wrappedProtocol.getHandle = proto.getHandle
        return proto.wrappedProtocol

class TorSSLObservatory(TorTest):
    name = "Tor SSL Observatory"
    version = "0.1"
    description = "Fetch the certificate chain of HTTPS URLs over Tor exits"

    inputFile = ['file', 'f', None,
            'List of URLS to perform GET requests to']
    requiredOptions = ['file']

    @defer.inlineCallbacks
    def setUp(self): 
        # XXX review these values
        d = yield self.state.protocol.set_conf(
                "UseEntryGuards", "0",
                "MaxClientCircuitsPending", "128",
                "SocksTimeout", "30",
                "CircuitIdleTimeout", "30")

    def test_fetch_cert_chain(self):
        exit_hex, url = self.input

        try:
            exit = self.state.routers[exit_hex]
        except KeyError:
            # Router not in consensus, sorry
            self.report['failure'] = "Router %s not in consensus." % self.input
            return

        if "https" in url.split(":")[0]: port = 443
        else: port = 80
            
        host = url.split("//")[1].strip()
        addr = (host,port)
        
        _endpoint = self.getExitSpecificEndpoint(addr, exit)
        ctx = ClientContextFactory()
        endpoint = haxendpoint(ctx, _endpoint)

        gotCertChain = defer.Deferred()

        class DropCertChainProto(Protocol):
            def connectionMade(self):
                #XXX: send some plausible noise
                self.transport.write(
"""GET / HTTP/1.1
Host: %s
User-Agent: Mozilla/5.0 (Windows NT 6.1; rv:17.0) Gecko/20100101 Firefox/17.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-us,en;q=0.5
Accept-Encoding: gzip, deflate
Connection: keep-alive

""" % host)
            def dataReceived(self, data):
                if gotCertChain.called: return
                cert_chain = self.getHandle().get_peer_cert_chain()
                self.transport.loseConnection()
                gotCertChain.callback(cert_chain)
            
        class DropCertChain(ClientFactory):
            protocol = DropCertChainProto

        d = endpoint.connect(DropCertChain())

        def addCertChainToReport(cert_chain, report):
            pem_chain = []
            for cert in cert_chain:
                pem_chain.append(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
            report['cert_chain'] = pem_chain

        gotCertChain.addCallback(addCertChainToReport, self.report)
        def errback(err): 
            self.report['failure'] = errors.handleAllFailures(y)
        gotCertChain.addErrback(errback)
        return gotCertChain

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

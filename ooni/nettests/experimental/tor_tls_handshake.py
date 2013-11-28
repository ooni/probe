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

firefox_ciphers = ["ECDHE-ECDSA-AES256-SHA",
                   "ECDHE-RSA-AES256-SHA",
                   "DHE-RSA-CAMELLIA256-SHA",
                   "DHE-DSS-CAMELLIA256-SHA",
                   "DHE-RSA-AES256-SHA",
                   "DHE-DSS-AES256-SHA",
                   "ECDH-ECDSA-AES256-CBC-SHA",
                   "ECDH-RSA-AES256-CBC-SHA",
                   "CAMELLIA256-SHA",
                   "AES256-SHA",
                   "ECDHE-ECDSA-RC4-SHA",
                   "ECDHE-ECDSA-AES128-SHA",
                   "ECDHE-RSA-RC4-SHA",
                   "ECDHE-RSA-AES128-SHA",
                   "DHE-RSA-CAMELLIA128-SHA",
                   "DHE-DSS-CAMELLIA128-SHA",]

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
                "MaxClientCircuitsPending", "128",
                "SocksTimeout", "30",
                "CircuitIdleTimeout", "30")

    def test_fetch_cert_chain(self):
        exit_hex, url = self.input

        try:
            exit = self.state.routers[exit_hex]
        except KeyError:
            # Router not in consensus, sorry
            self.report['failure'] = "Router %s not in consensus." % exit_hex
            return

        if "https" in url.split(":")[0]: port = 443
        else: port = 80
            
        host = url.split("//")[1].strip()
        addr = (host,port)
        
        _endpoint = self.getExitSpecificEndpoint(addr, exit)
        ctx = ClientContextFactory()
        ciphersuite = ":".join(firefox_ciphers)
        ctx.getContext().set_cipher_list(ciphersuite)

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
                ssl_data={}
                ssl_data['cert_chain'] = self.getHandle().get_peer_cert_chain()
                #XXX: get_cipher_list() does not return the expected set of ciphers :'(
                #ssl_data['cipher_list'] = self.getHandle().get_cipher_list()
                self.transport.loseConnection()
                gotCertChain.callback(ssl_data)
            
        class DropCertChain(ClientFactory):
            protocol = DropCertChainProto

        d = endpoint.connect(DropCertChain())
        d.addErrback(gotCertChain.errback)

        def addCertChainToReport(ssl_data, report):
            cert_chain = ssl_data['cert_chain']
            pem_chain = []
            for cert in cert_chain:
                pem_chain.append(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
            report['cert_chain'] = pem_chain
            #report['cipher_list'] = ssl_data['cipher_list']

        gotCertChain.addCallback(addCertChainToReport, self.report)
        def errback(err): 
            self.report['failure'] = errors.handleAllFailures(err)
        gotCertChain.addErrback(errback)
        return gotCertChain

    def getInputProcessor(self):
        if self.inputFileSpecified:
            self.inputFilename = self.localOptions[self.inputFile[0]]
            urls = open(self.inputFilename)

            for url in urls:
                for r in self.exits:
                    yield (r.id_hex, url.strip())

from twisted.internet import protocol, defer, reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.nettest import NetTestCase
from ooni.utils import log

class TCPSender(protocol.Protocol):
    report = None
    def dataReceived(self, data):
        self.report['received'].append(data)

    def sendPayload(self, payload):
        self.report['sent'].append(payload)
        self.transport.write(payload)

class TCPSenderFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return TCPSender()

class TCPTest(NetTestCase):
    name = "Base TCP Test"
    version = "0.1"

    requiresRoot = False
    timeout = 2
    address = None
    port = None

    def _setUp(self):
        self.report['sent'] = []
        self.report['received'] = []

    def sendPayload(self, payload):
        d1 = defer.Deferred()

        def closeConnection(p):
            p.transport.loseConnection()
            log.debug("Closing connection")
            d1.callback(None)

        def errback(failure):
            self.report['error'] = str(failure)
            log.exception(failure)

        def connected(p):
            log.debug("Connected to %s:%s" % (self.address, self.port))
            p.report = self.report
            p.sendPayload(payload)
            reactor.callLater(self.timeout, closeConnection, p)

        point = TCP4ClientEndpoint(reactor, self.address, self.port)
        d2 = point.connect(TCPSenderFactory())
        d2.addCallback(connected)
        d2.addErrback(errback)
        return d1



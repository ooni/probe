from twisted.internet import protocol, defer, reactor
from twisted.internet.error import ConnectionDone
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.nettest import NetTestCase
from ooni.utils import log

class TCPSender(protocol.Protocol):
    report = None
    payload_len = None
    received_data = ''
    def dataReceived(self, data):
        """
        We receive data until the total amount of data received reaches that
        which we have sent. At that point we append the received data to the
        report and we fire the callback of the test template sendPayload
        function.

        This is used in pair with a TCP Echo server.

        The reason why we put the data received inside of an array is that in
        future we may want to expand this to support state and do something
        similar to what daphne does, but without the mutation.

        XXX Actually daphne will probably be refactored to be a subclass of the
        TCP Test Template.
        """
        if self.payload_len:
            self.received_data += data
            if len(self.received_data) >= self.payload_len:
                self.transport.loseConnection()
                self.report['received'].append(data)
                self.deferred.callback(self.report['received'])

    def sendPayload(self, payload):
        """
        Write the payload to the wire and set the expected size of the payload
        we are to receive.
        """
        self.payload_len = len(payload)
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
            d1.callback(self.report['received'])

        def errback(failure):
            self.report['error'] = str(failure)
            log.exception(failure)
            d1.callback(self.report['received'])

        def connected(p):
            log.debug("Connected to %s:%s" % (self.address, self.port))
            p.report = self.report
            p.deferred = d1
            p.sendPayload(payload)
            reactor.callLater(self.timeout, closeConnection, p)

        point = TCP4ClientEndpoint(reactor, self.address, self.port)
        d2 = point.connect(TCPSenderFactory())
        d2.addCallback(connected)
        d2.addErrback(errback)
        return d1



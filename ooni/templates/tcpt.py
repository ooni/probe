from twisted.internet import protocol, defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.nettest import NetTestCase
from ooni.errors import failureToString
from ooni.utils import log

class TCPSender(protocol.Protocol):
    def __init__(self):
        self.received_data = ''
        self.sent_data = ''

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

    def sendPayload(self, payload):
        """
        Write the payload to the wire and set the expected size of the payload
        we are to receive.

        Args:

            payload: the data to be sent on the wire.

        """
        self.payload_len = len(payload)
        self.sent_data = payload
        self.transport.write(payload)

class TCPSenderFactory(protocol.Factory):
    noisy = False
    def buildProtocol(self, addr):
        return TCPSender()

class TCPTest(NetTestCase):
    name = "Base TCP Test"
    version = "0.1"

    requiresRoot = False
    timeout = 5
    address = None
    port = None

    def _setUp(self):
        super(TCPTest, self)._setUp()

        self.report['sent'] = []
        self.report['received'] = []

    def sendPayload(self, payload):
        d1 = defer.Deferred()

        def closeConnection(proto):
            self.report['sent'].append(proto.sent_data)
            self.report['received'].append(proto.received_data)
            proto.transport.loseConnection()
            log.debug("Closing connection")
            d1.callback(proto.received_data)

        def timedOut(proto):
            self.report['failure'] = 'tcp_timed_out_error'
            proto.transport.loseConnection()

        def errback(failure):
            self.report['failure'] = failureToString(failure)
            d1.errback(failure)

        def connected(proto):
            log.debug("Connected to %s:%s" % (self.address, self.port))
            proto.report = self.report
            proto.deferred = d1
            proto.sendPayload(payload)
            if self.timeout:
                # XXX-Twisted this logic should probably go inside of the protocol
                reactor.callLater(self.timeout, closeConnection, proto)

        point = TCP4ClientEndpoint(reactor, self.address, self.port)
        log.debug("Connecting to %s:%s" % (self.address, self.port))
        d2 = point.connect(TCPSenderFactory())
        d2.addCallback(connected)
        d2.addErrback(errback)
        return d1

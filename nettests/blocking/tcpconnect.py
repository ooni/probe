# -*- encoding: utf-8 -*-
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

from twisted.internet.error import ConnectionRefusedError
from twisted.internet.error import TCPTimedOutError, TimeoutError

from ooni import nettest
from ooni.nettest import handleAllFailures
from ooni.utils import log

class TCPFactory(Factory):
    def buildProtocol(self, addr):
        return Protocol()

class TCPConnectTest(nettest.NetTestCase):
    name = "TCP Connect"
    author = "Arturo Filastò"
    version = "0.1"
    inputFile = ['file', 'f', None,
            'File containing the IP:PORT combinations to be tested, one per line']

    requiredOptions = ['file']
    def test_connect(self):
        """
        This test performs a TCP connection to the remote host on the specified port.
        the report will contains the string 'success' if the test has
        succeeded, or the reason for the failure if it has failed.
        """
        host, port = self.input.split(":")
        def connectionSuccess(protocol):
            protocol.transport.loseConnection()
            log.debug("Got a connection to %s" % self.input)
            self.report["connection"] = 'success'

        def connectionFailed(failure):
            self.report['connection'] = handleAllFailures(failure)

        from twisted.internet import reactor
        point = TCP4ClientEndpoint(reactor, host, int(port))
        d = point.connect(TCPFactory())
        d.addCallback(connectionSuccess)
        d.addErrback(connectionFailed)
        return d


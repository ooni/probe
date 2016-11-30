# -*- encoding: utf-8 -*-
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni import nettest
from ooni.errors import handleAllFailures
from ooni.utils import log


class TCPFactory(Factory):

    def buildProtocol(self, addr):
        return Protocol()


class TCPConnectTest(nettest.NetTestCase):
    name = "TCP Connect"
    description = "Performs a TCP connect scan of all the " \
                  "host port combinations given as input."
    author = "Arturo Filastò"
    version = "0.2.0"
    inputFile = [
        'file',
        'f',
        None,
        'File containing the IP:PORT combinations to be tested, one per line.']

    requiresTor = False
    requiresRoot = False
    requiredOptions = ['file']

    def setUp(self):
        def strip_url(address):
            proto, path = address.strip().split('://')
            proto = proto.lower()
            host = path.split('/')[0]
            if proto == 'http':
                return host, 80
            if proto == 'https':
                return host, 443

        pluggable_transports = (
            "obfs3", "obfs2", "fte", "scramblesuit",
            "obfs4"
        )
        def is_bridge_line(line):
            first = line.split(" ")[0]
            return first.lower() in pluggable_transports + ("bridge",)
        def strip_bridge(line):
            if line.lower().startswith("bridge"):
                return line.split(" ")[2].split(":")
            return line.split(" ")[1].split(":")

        if self.input.startswith("http"):
            host, port = strip_url(self.input)
        elif is_bridge_line(self.input):
            host, port = strip_bridge(self.input)
        else:
            host, port = self.input.split(" ")[0].split(":")

        self.host = host
        self.port = port

    def test_connect(self):
        """
        This test performs a TCP connection to the remote host on the
        specified port.
        The report will contains the string 'success' if the test has
        succeeded, or the reason for the failure if it has failed.
        """
        def connectionSuccess(protocol):
            protocol.transport.loseConnection()
            log.debug("Got a connection to %s" % self.input)
            self.report["connection"] = 'success'

        def connectionFailed(failure):
            self.report['connection'] = handleAllFailures(failure)

        from twisted.internet import reactor
        point = TCP4ClientEndpoint(reactor, self.host, int(self.port))
        d = point.connect(TCPFactory())
        d.addCallback(connectionSuccess)
        d.addErrback(connectionFailed)
        return d

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
    version = "0.1"
    inputFile = [
        'file',
        'f',
        None,
        'File containing the IP:PORT combinations to be tested, one per line.']

    requiresTor = False
    requiresRoot = False
    requiredOptions = ['file']

    def test_connect(self):
        """
        This test performs a TCP connection to the remote host on the
        specified port.
        The report will contains the string 'success' if the test has
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

    def inputProcessor(self, filename=None):
        """
        This inputProcessor extracts name:port pairs from urls
        XXX: Does not support unusual port numbers
        """
        def strip_url(address):
            proto, path = x.strip().split('://')
            proto = proto.lower()
            host = path.split('/')[0]
            if proto == 'http':
                return "%s:80" % host
            if proto == 'https':
                return "%s:443" % host

        pluggable_transports = ("obfs3", "obfs2", "fte", "scramblesuit")
        def is_bridge_line(line):
            first = line.split(" ")[0]
            return first.lower() in pluggable_transports + ("bridge",)
        def strip_bridge(line):
            if line.lower().startswith("Bridge"):
                return line.split(" ")[2]
            return line.split(" ")[1]

        if filename:
            fp = open(filename)
            for x in fp.readlines():
                if x.startswith("http"):
                    yield strip_url(x)
                elif is_bridge_line(x):
                    yield strip_bridge(x)
                else:
                    yield x.split(" ")[0]
            fp.close()
        else:
            pass

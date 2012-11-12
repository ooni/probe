
from twisted.internet.protocol import Protocol, Factory, ServerFactory
from twisted.internet.error import ConnectionDone

from oonib import config

from ooni.kit.daphn3 import Daphn3Protocol
from ooni.kit.daphn3 import read_pcap, read_yaml

class TCPEchoProtocol(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

class TCPEchoHelper(Factory):
    """
    A very simple echo protocol implementation
    """
    protocol = TCPEchoProtocol

daphn3Steps = [{'client': '\x00\x00\x00'}, 
        {'server': '\x00\x00\x00'}]

class Daphn3Server(ServerFactory):
    """
    This is the main class that deals with the daphn3 server side component.
    We keep track of global state of every client here.
    Every client is identified by their IP address and the state of mutation is
    stored by using their IP address as a key. This may lead to some bugs if
    two different clients are sharing the same IP, but hopefully the
    probability of such thing is not that likely.
    """
    protocol = Daphn3Protocol
    def buildProtocol(self, addr):
        p = self.protocol(steps=daphn3Steps, 
                role="server")
        p.factory = self
        return p


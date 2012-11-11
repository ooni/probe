
from twisted.internet.protocol import Protocol, Factory, ServerFactory
from twisted.internet.error import ConnectionDone

from oonib import config

from ooni.kit.daphn3 import Mutator, Daphn3Protocol
from ooni.kit.daphn3 import read_pcap, read_yaml

class TCPEchoProtocol(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

class TCPEchoHelper(Factory):
    """
    A very simple echo protocol implementation
    """
    protocol = TCPEchoProtocol

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
    mutations = {}
    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self

        if config.daphn3.yaml_file:
            steps = read_yaml(config.daphn3.yaml_file)
        elif config.daphn3.pcap_file:
            steps = read_pcap(config.daphn3.pcap_file)
        else:
            print "Error! No PCAP, nor YAML file provided."
            steps = None

        p.factory.steps = steps

        if addr.host not in self.mutations:
            self.mutations[addr.host] = Mutator(p.steps)
        else:
            print "Moving on to next mutation"
            if not self.mutations[addr.host].next():
                self.mutations.pop(addr.host)
        try:
            p.mutator = self.mutations[addr.host]
            p.current_state = p.mutator.state()
        except:
            pass
        return p


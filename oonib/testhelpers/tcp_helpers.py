
from twisted.internet.protocol import Protocol, Factory, ServerFactory
from twisted.internet.error import ConnectionDone

from oonib import config
from ooni.utils import log
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

if config.helpers.daphn3.yaml_file:
    daphn3Steps = read_pcap(config.helpers.daphn3.yaml_file)

elif config.helpers.daphn3.pcap_file:
    daphn3Steps = read_yaml(config.helpers.daphn3.pcap_file)

else:
    daphn3Steps = [{'client': 'client_packet'}, 
        {'server': 'server_packet'}]

class Daphn3ServerProtocol(Daphn3Protocol):
    def nextStep(self):
        log.debug("Moving on to next step in the state walk")
        self.current_data_received = 0
        # Python why?
        if self.current_step >= (len(self.steps) - 1):
            log.msg("Reached the end of the state machine")
            log.msg("Censorship fingerpint bisected!")
            step_idx, mutation_idx = self.factory.mutation
            log.msg("step_idx: %s | mutation_id: %s" % (step_idx, mutation_idx))
            #self.transport.loseConnection()
            if self.report:
                self.report['mutation_idx'] = mutation_idx
                self.report['step_idx'] = step_idx
            return
        else:
            self.current_step += 1
        if self._current_step_role() == self.role:
            # We need to send more data because we are again responsible for
            # doing so.
            self.sendPayload()

class Daphn3Server(ServerFactory):
    """
    This is the main class that deals with the daphn3 server side component.
    We keep track of global state of every client here.
    Every client is identified by their IP address and the state of mutation is
    stored by using their IP address as a key. This may lead to some bugs if
    two different clients are sharing the same IP, but hopefully the
    probability of such thing is not that likely.
    """
    protocol = Daphn3ServerProtocol
    # step_idx, mutation_idx
    mutation = [0, 0]
    def buildProtocol(self, addr):
        p = self.protocol()
        p.steps = daphn3Steps
        p.role = "server"
        p.factory = self
        return p




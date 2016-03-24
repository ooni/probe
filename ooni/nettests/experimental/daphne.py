# -*- encoding: utf-8 -*-
from twisted.python import usage
from twisted.internet import protocol, endpoints, reactor

from ooni import nettest
from ooni.kit import daphn3
from ooni.utils import log

class Daphn3ClientProtocol(daphn3.Daphn3Protocol):
    def nextStep(self):
        log.debug("Moving on to next step in the state walk")
        self.current_data_received = 0
        if self.current_step >= (len(self.steps) - 1):
            log.msg("Reached the end of the state machine")
            log.msg("Censorship fingerprint bisected!")
            step_idx, mutation_idx = self.factory.mutation
            log.msg("step_idx: %s | mutation_id: %s" % (step_idx, mutation_idx))
            #self.transport.loseConnection()
            if self.report:
                self.report['mutation_idx'] = mutation_idx
                self.report['step_idx'] = step_idx
            self.d.callback(None)
            return
        else:
            self.current_step += 1
        if self._current_step_role() == self.role:
            # We need to send more data because we are again responsible for
            # doing so.
            self.sendPayload()


class Daphn3ClientFactory(protocol.ClientFactory):
    protocol = daphn3.Daphn3Protocol
    mutation = [0,0]
    steps = None

    def buildProtocol(self, addr):
        p = self.protocol()
        p.steps = self.steps
        p.factory = self
        return p

    def startedConnecting(self, connector):
        log.msg("Started connecting %s" % connector)

    def clientConnectionFailed(self, reason, connector):
        log.err("We failed connecting the the OONIB")
        log.err("Cannot perform test. Perhaps it got blocked?")
        log.err("Please report this to tor-assistants@torproject.org")

    def clientConnectionLost(self, reason, connector):
        log.err("Daphn3 client connection lost")
        print reason

class daphn3Args(usage.Options):
    optParameters = [
                     ['host', 'h', '127.0.0.1', 'Target Hostname'],
                     ['port', 'p', 57003, 'Target port number']]

    optFlags = [['pcap', 'c', 'Specify that the input file is a pcap file'],
                ['yaml', 'y', 'Specify that the input file is a YAML file (default)']]

class daphn3Test(nettest.NetTestCase):

    name = "Daphn3"
    description = "Bisects the censors fingerprint by mutating the given input packets."
    usageOptions = daphn3Args
    inputFile = ['file', 'f', None, 
            'Specify the pcap or YAML file to be used as input to the test']

    #requiredOptions = ['file']
    requiresRoot = False
    requiresTor = False
    steps = None

    def inputProcessor(self, filename):
        """
        step_idx is the step in the packet exchange
        ex.
        [.X.] are packets sent by a client or a server

            client:  [.1.]        [.3.] [.4.]
            server:         [.2.]             [.5.]

        mutation_idx: is the sub index of the packet as in the byte of the
        packet at the step_idx that is to be mutated

        """
        if self.localOptions['pcap']:
            daphn3Steps = daphn3.read_pcap(filename)
        else:
            daphn3Steps = daphn3.read_yaml(filename)
        log.debug("Loaded these steps %s" % daphn3Steps)
        yield daphn3Steps

    def test_daphn3(self):
        host = self.localOptions['host']
        port = int(self.localOptions['port'])

        def failure(failure):
            log.msg("Failed to connect")
            self.report['censored'] = True
            self.report['mutation'] = 0
            raise Exception("Error in connection, perhaps the backend is censored")
            return

        def success(protocol):
            log.msg("Successfully connected")
            protocol.sendPayload()
            return protocol.d

        log.msg("Connecting to %s:%s" % (host, port))
        endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port)
        daphn3_factory = Daphn3ClientFactory()
        daphn3_factory.steps = self.input
        daphn3_factory.report = self.report
        d = endpoint.connect(daphn3_factory)
        d.addErrback(failure)
        d.addCallback(success)
        return d


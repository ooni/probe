# -*- encoding: utf-8 -*-
from twisted.python import usage
from twisted.internet import protocol, endpoints, reactor

from ooni import nettest
from ooni.kit import daphn3
from ooni.utils import log

class Daphn3ClientFactory(protocol.ClientFactory):
    protocol = daphn3.Daphn3Protocol
    def __init__(self, steps):
        self.steps = steps

    def buildProtocol(self, addr):
        p = self.protocol(steps=self.steps)
        p.factory = self
        return p

    def startedConnecting(self, connector):
        print "Started connecting %s" % connector

    def clientConnectionFailed(self, reason, connector):
        log.err("We failed connecting the the OONIB")
        log.err("Cannot perform test. Perhaps it got blocked?")
        log.err("Please report this to tor-assistants@torproject.org")

    def clientConnectionLost(self, reason, connector):
        log.err("Daphn3 client connection lost")
        print reason


class daphn3Args(usage.Options):
    optParameters = [
                     ['host', 'h', None, 'Target Hostname'],
                     ['port', 'p', None, 'Target port number']]

    optFlags = [['pcap', 'c', 'Specify that the input file is a pcap file'],
                ['yaml', 'y', 'Specify that the input file is a YAML file (default)']]

class daphn3Test(nettest.NetTestCase):

    name = "Daphn3"
    usageOptions = daphn3Args
    inputFile = ['file', 'f', None, 
            'Specify the pcap or YAML file to be used as input to the test']

    #requiredOptions = ['file']

    steps = None

    def inputProcessor(self, fp):
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
            daphn3Steps = daphn3.read_pcap(self.localOptions['pcap'])
        elif self.localOptions['yaml']:
            daphn3Steps = daphn3.read_yaml(self.localOptions['yaml'])
        else:
            daphn3Steps = [{'client': 'testing'}, {'server': 'antani'}]

        for idx, step in enumerate(daphn3Steps):
            current_packet = step.values()[0]
            for mutation_idx in range(len(current_packet)):
                if step.keys()[0] == "client":
                    mutated_step = daphn3.daphn3Mutate(daphn3Steps,
                            idx, mutation_idx)
                    yield mutated_step
                else:
                    yield daphn3Steps

    def setUp(self):
        self.factory = Daphn3ClientFactory(self.input)
        self.factory.report = self.report
        print "Just set the factory to %s with %s" % (self.factory, 
                self.input)

    def test_daphn3(self):
        host = self.localOptions['host']
        port = int(self.localOptions['port'])

        def failure(failure):
            log.msg("Failed to connect")
            self.report['censored'] = True
            self.report['mutation'] = 0

        def success(protocol):
            log.msg("Successfully connected")
            protocol.sendMutation()

        log.msg("Connecting to %s:%s" % (host, port))
        endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port)
        d = endpoint.connect(self.factory)
        d.addErrback(failure)
        d.addCallback(success)
        return d


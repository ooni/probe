from twisted.python import usage
from twisted.internet import protocol, endpoints, reactor

from ooni.kit import daphn3
from ooni.utils import log

class Daphn3ClientProtocol(daphn3.Daphn3Protocol):
    def connectionMade(self):
        self.next_state()

class Daphn3ClientFactory(protocol.ClientFactory):
    protocol = Daphn3ClientProtocol
    mutator = None
    steps = None
    test = None

    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self
        p.test = self.test

        if self.steps:
            p.steps = self.steps

        if not self.mutator:
            self.mutator = daphn3.Mutator(p.steps)

        else:
            print "Moving on to next mutation"
            self.mutator.next()

        p.mutator = self.mutator
        p.current_state = self.mutator.state()
        return p

    def clientConnectionFailed(self, reason):
        print "We failed connecting the the OONIB"
        print "Cannot perform test. Perhaps it got blocked?"
        print "Please report this to tor-assistants@torproject.org"
        self.test.result['error'] = ('Failed in connecting to OONIB', reason)
        self.test.end(d)

    def clientConnectionLost(self, reason):
        print "Connection Lost."

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

    requiredOptions = ['file']

    steps = None

    def inputProcessor(self, fp):
        if self.localOptions['pcap']:
            self.steps = daphn3.read_pcap(self.localOptions['pcap'])
        else:
            self.steps = daphn3.read_yaml(self.localOptions['yaml'])

    def setUp(self):
        self.factory = Daphn3ClientFactory()
        self.factory.test = self

        if self.localOptions['pcap']:
            self.steps = daphn3.read_pcap(self.localOptions['pcap'])
        elif self.localOptions['yaml']:
            self.steps = daphn3.read_yaml(self.localOptions['yaml'])
        else:
            raise usage.UsageError("You must specify either --pcap or --yaml")

        mutations = 0
        for x in self.steps:
            mutations += len(x['data'])
        return {'mutation': range(mutations)}

    def control(self, exp_res, args):
        try:
            mutation = self.factory.mutator.get(0)
            self.result['censored'] = False
        except:
            mutation = None

        return {'mutation_number': args['mutation'],
                'value': mutation}

    def _failure(self, *argc, **kw):
        self.report['censored'] = True
        self.report['mutation'] = 
        self.report['error'] = ('Failed in connecting', (argc, kw))

    def test_daphn3(self):
        log.msg("Doing mutation %s" % args['mutation'])
        self.factory.steps = self.steps

        host = self.local_options['host']
        port = int(self.local_options['port'])
        log.msg("Connecting to %s:%s" % (host, port))

        endpoint = endpoints.TCP4ClientEndpoint(reactor, host, port)
        d = endpoint.connect(self.factory)
        d.addErrback(self._failure)
        return d


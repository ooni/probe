"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, endpoints

from ooni.plugoo import reports
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.protocols import daphn3
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
    optParameters = [['pcap', 'f', None,
                        'PCAP to read for generating the YAML output'],

                     ['output', 'o', 'daphn3.yaml',
                        'What file should be written'],

                     ['yaml', 'y', None,
                        'The input file to the test'],

                     ['host', 'h', None, 'Target Hostname'],
                     ['port', 'p', None, 'Target port number'],
                     ['resume', 'r', 0, 'Resume at this index']]

class daphn3Test(OONITest):
    implements(IPlugin, ITest)

    shortName = "daphn3"
    description = "daphn3"
    requirements = None
    options = daphn3Args
    blocking = False

    local_options = None

    steps = None

    def initialize(self):
        if not self.local_options:
            self.end()
            return

        self.factory = Daphn3ClientFactory()
        self.factory.test = self

        if self.local_options['pcap']:
            self.tool = True

        elif self.local_options['yaml']:
            self.steps = daphn3.read_yaml(self.local_options['yaml'])

        else:
            log.msg("Not enough inputs specified to the test")
            self.end()

    def runTool(self):
        import yaml
        pcap = daphn3.read_pcap(self.local_options['pcap'])
        f = open(self.local_options['output'], 'w')
        f.write(yaml.dump(pcap))
        f.close()

    def control(self, exp_res, args):
        try:
            mutation = self.factory.mutator.get(0)
            self.result['censored'] = False
        except:
            mutation = None

        return {'mutation_number': args['mutation'],
                'value': mutation}

    def _failure(self, *argc, **kw):
        self.result['censored'] = True
        self.result['error'] = ('Failed in connecting', (argc, kw))
        self.end()

    def experiment(self, args):
        log.msg("Doing mutation %s" % args['mutation'])
        self.factory.steps = self.steps
        host = self.local_options['host']
        port = int(self.local_options['port'])
        log.msg("Connecting to %s:%s" % (host, port))

        if self.ended:
            return

        endpoint = endpoints.TCP4ClientEndpoint(self.reactor, host, port)
        d = endpoint.connect(self.factory)
        d.addErrback(self._failure)
        return d

    def load_assets(self):
        if not self.local_options:
            return {}
        if not self.steps:
            print "Error: No assets!"
            self.end()
            return {}
        mutations = 0
        for x in self.steps:
            mutations += len(x['data'])
        return {'mutation': range(mutations)}

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
daphn3test = daphn3Test(None, None, None)

"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, endpoints

from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.protocols import daphn3
from ooni.utils import log

class Daphn3ClientProtocol(daphn3.Daphn3Protocol):
    def connectionMade(self):
        self.next_state()

    def connectionLost(self, reason):
        print "LOST!"

class Daphn3ClientFactory(protocol.ClientFactory):
    protocol = Daphn3ClientProtocol
    mutator = None
    steps = None

    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self
        if self.steps:
            p.steps = self.steps

        if not self.mutator:
            self.mutator = daphn3.Mutator(p.steps)
            p.mutator = self.mutator
        else:
            print "Moving on to next mutation"
            self.mutator.next_mutation()
        return p

    def clientConnectionFailed(self, reason):
        print "We failed connecting the the OONIB"
        print "Cannot perform test. Perhaps it got blocked?"
        print "Please report this to tor-assistants@torproject.org"

    def clientConnectionLost(self, reason):
        print "Connection Lost."

class daphn3Args(usage.Options):
    optParameters = [['pcap', 'f', None, 'PCAP file to take as input'],
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
            return
        #pass
        self.factory = Daphn3ClientFactory()
        self.steps = daphn3.get_daphn3_dictionary_from_pcap(self.local_options['pcap'])

    def control(self, exp_res, args):
        mutation = self.factory.mutator.get_mutation(0)
        return {'mutation_number': args['mutation'], 'value': mutation}

    def experiment(self, args):
        log.msg("Doing mutation %s" % args['mutation'])
        self.factory.steps = self.steps
        host = self.local_options['host']
        port = int(self.local_options['port'])
        log.msg("Connecting to %s:%s" % (host, port))
        endpoint = endpoints.TCP4ClientEndpoint(self.reactor, host, port)
        return endpoint.connect(self.factory)
        #return endpoint.connect(Daphn3ClientFactory)

    def load_assets(self):
        if not self.steps:
            print "No asset!"
            return {}
        mutations = 0
        for x in self.steps:
            mutations += len(x['data'])
        return {'mutation': range(mutations)}

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
daphn3test = daphn3Test(None, None, None)

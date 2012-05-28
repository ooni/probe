from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from plugoo.tests import ITest, TwistedTest
from twisted.internet import threads

from tests.bridget import BridgeT as BridgeTlegacy
from tests.bridget import BridgeTAsset as BridgeTAsset
from ooniprobe import ooni

o = ooni()

class BridgetArgs(usage.Options):
    optParameters = [['asset', 'a', None, 'Asset file'],
                     ['resume', 'r', 0, 'Resume at this index'],
                     ['bridge', 'b', None, 'Specify a single bridge']]

class BridgeT(TwistedTest):
    implements(IPlugin, ITest)

    shortName = "bridget"
    description = "Bridget plugin"
    requirements = None
    options = BridgetArgs

    def experiment(self):
        bridget = BridgeTlegacy(o)
        o.logger.info("Starting bridget test")
        print "ASSET:%s " % self.asset
        d = threads.deferToThread(bridget.connect, self.asset)
        d.addCallback(self.d_experiment.callback, None)
        return d

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
bridget = BridgeT(None, None)

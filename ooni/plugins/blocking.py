from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin

from ooni.plugoo.assets import Asset
from ooni.plugoo.tests import ITest, OONITest

class BlockingArgs(usage.Options):
    optParameters = [['asset', 'a', None, 'Asset file'],
                     ['resume', 'r', 0, 'Resume at this index'],
                     ['shit', 'o', None, 'Other arguments']]

class BlockingTest(OONITest):
    implements(IPlugin, ITest)

    shortName = "blocking"
    description = "Blocking plugin"
    requirements = None
    options = BlockingArgs
    # Tells this to be blocking.
    blocking = True

    def control(self, experiment_result, args):
        print "Experiment Result:", experiment_result
        print "Args", args
        return experiment_result

    def experiment(self, args):
        import urllib
        req = urllib.urlopen(args['asset'])
        return {'page': req.readlines()}

    def load_assets(self):
        if self.local_options:
            return {'asset': Asset(self.local_options['asset'])}
        else:
            return {}

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
blocking = BlockingTest(None, None, None)

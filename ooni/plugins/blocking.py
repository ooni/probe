from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin

from plugoo.assets import Asset
from plugoo.tests import ITest, OONITest

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
        url = 'http://torproject.org/' if not 'asset' in args else args['asset']
        try:
            req = urllib.urlopen(url)
        except:
            return {'error': 'Connection failed!'}

        return {'page': req.readlines()}

    def load_assets(self):
        if self.local_options and self.local_options['asset']:
            return {'asset': Asset(self.local_options['asset'])}
        else:
            return {}

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
blocking = BlockingTest(None, None, None)

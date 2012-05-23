from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from plugoo.tests import ITest, TwistedTest

class SkelArgs(usage.Options):
    optParameters = [['asset', 'a', None, 'Asset file'],
                     ['resume', 'r', 0, 'Resume at this index']]

class SkelTest(TwistedTest):
    implements(IPlugin, ITest)

    shortName = "skeleton"
    description = "Skeleton plugin"
    requirements = None
    options = SkelArgs

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
skel = SkelTest(None, None)

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from plugoo.tests import ITest

class SkelArgs(usage.Options):
    optParameters = [['assets', 'a', None, 'Asset file'],
                     ['resume', 'r', None, 'Resume at this index']]

class SkelTest(object):
    implements(IPlugin, ITest)

    shortName = "skeleton"
    description = "Skeleton plugin"
    requirements = None
    arguments = SkelArgs

    def startTest():
        pass

skel = SkelTest()


from twisted.internet import defer, base
from twisted.trial import unittest

from ooni.director import Director
from ooni.nettest import NetTestLoader
from tests.mocks import MockReporter
base.DelayedCall.debug = True

net_test_string = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham']]

class DummyTestCase(NetTestCase):
    inputFile = ['file', 'f', None, 'The input File']

    usageOptions = UsageOptions

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'
"""


dummyArgs = ('--spam', 1, '--file', 'dummyInputFile.txt')

class TestDirector(unittest.TestCase):
    timeout = 1
    def setUp(self):
        with open('dummyInputFile.txt', 'w') as f:
            for i in range(10):
                f.write("%s\n" % i)

        self.reporters = [MockReporter()]
        self.director = Director()

    def tearDown(self):
        pass

    def test_start_net_test(self):
        options = {'test':net_test_string, 'subargs':dummyArgs}
        net_test_loader = NetTestLoader(options)
        net_test_loader.checkOptions()
        d = self.director.startNetTest('', net_test_loader, self.reporters)

        @d.addCallback
        def done(result):
            self.assertEqual(self.director.successfulMeasurements, 20)

        return d

    def test_stop_net_test(self):
        pass


from twisted.internet import defer, base
from twisted.trial import unittest

from ooni.director import Director
base.DelayedCall.debug = True
class MockMeasurement(object):
    def run(self):
        return defer.succeed(42)

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


dummyOptions = {'spam': 1, 'file': 'dummyInputFile.txt'}

class MockReporter(object):
    def __init__(self):
        self.created = defer.succeed(None)

    def createReport(self):
        pass

    def write(self):
        pass

class TestDirector(unittest.TestCase):
    timeout = 1
    def setUp(self):
        with open('dummyInputFile.txt', 'w') as f:
            for i in range(10):
                f.write("%s\n" % i)

        reporters = [MockReporter]
        self.director = Director(reporters)

    def tearDown(self):
        pass

    def test_start_net_test(self):
        d = self.director.startTest(net_test_string, dummyOptions)

        @d.addCallback
        def done(result):
            print "SOMETHING"
            self.assertEqual(self.director.successfulMeasurements, 20)

        return d

    def test_stop_net_test(self):
        pass


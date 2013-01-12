import os
from StringIO import StringIO
from tempfile import TemporaryFile, mkstemp

from twisted.trial import unittest
from twisted.internet import defer, reactor

from ooni.nettest import NetTest, InvalidOption, MissingRequiredOption
from ooni.nettest import FailureToLoadNetTest
from ooni.tasks import BaseTask

net_test_string = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', 'ham']]

class DummyTestCase(NetTestCase):
    usageOptions = UsageOptions

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'
"""

net_test_root_required = net_test_string+"""
    requiresRoot = True
"""

#XXX you should actually implement this
net_test_with_required_option = net_test_string

dummyInputs = range(1)
dummyOptions = {'spam': 'notham'}
dummyInvalidOptions = {'':''} # XXX: make invalid options
dummyOptionsWithRequiredOptions = {'':''} #XXX: set required options here

#dummyNetTest = NetTest(net_test_file, inputs, options)

class DummyMeasurement(BaseTask):
    def run(self):
        f = open('foo.txt', 'w')
        f.write('testing')
        f.close()

        return defer.succeed(self)

class DummyMeasurementFailOnce(BaseTask):
    def run(self):
        f = open('dummyTaskFailOnce.txt', 'w')
        f.write('fail')
        f.close()
        if self.failure >= 1:
            return defer.succeed()
        else:
            return defer.fail()

class DummyNetTest(NetTest):
    def __init__(self, num_measurements=1):
        NetTest.__init__(self, StringIO(net_test_string), dummyInputs, dummyOptions)
        self.num_measurements = num_measurements
    def generateMeasurements(self):
        for i in range(self.num_measurements):
            yield DummyMeasurement()

class DummyDirector(object):
    def __init__(self):
        pass

class DummyReporter(object):
    def __init__(self):
        pass
    def write(self, result):
        pass

class TestNetTest(unittest.TestCase):
    def assertCallable(self, thing):
        self.assertIn('__call__', dir(thing))

    def test_load_net_test_from_file(self):
        """
        Given a file verify that the net test cases are properly
        generated.
        """
        __, net_test_file = mkstemp()
        with open(net_test_file, 'w') as f:
            f.write(net_test_string)
        f.close()

        net_test_from_file = NetTest(net_test_file, dummyInputs,
                dummyOptions, DummyReporter())

        test_methods = set()
        for test_class, test_method in net_test_from_file.test_cases:
            instance = test_class()
            c = getattr(instance, test_method)
            self.assertCallable(c)

            test_methods.add(test_method)

        self.assertEqual(set(['test_a', 'test_b']), test_methods)

        os.unlink(net_test_file)

    def test_load_net_test_from_string(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        net_test_from_string = NetTest(StringIO(net_test_string),
                dummyInputs, dummyOptions, DummyReporter())

        test_methods = set()
        for test_class, test_method in net_test_from_string.test_cases:
            instance = test_class()
            c = getattr(instance, test_method)
            self.assertCallable(c)

            test_methods.add(test_method)

        self.assertEqual(set(['test_a', 'test_b']), test_methods)

    def test_load_with_option(self):
        self.assertIsInstance(NetTest(StringIO(net_test_string),
                    dummyInputs, dummyOptions, None), NetTest)

    #def test_load_with_invalid_option(self):
    #    #XXX: raises TypeError??
    #    self.assertRaises(InvalidOption, NetTest(StringIO(net_test_string), dummyInputs,
    #                dummyInvalidOptions, None))

    def test_load_with_required_option(self):
        self.assertIsInstance(NetTest(StringIO(net_test_with_required_option),
                dummyInputs, dummyOptionsWithRequiredOptions, None), NetTest)

    #def test_load_with_missing_required_option(self):
    #    #XXX: raises TypeError
    #    self.assertRaises(MissingRequiredOption,
    #            NetTest(StringIO(net_test_with_required_option), dummyInputs,
    #                dummyOptions, None))

    def test_require_root_succeed(self):
        #XXX: make root succeed
        NetTest(StringIO(net_test_root_required),
                dummyInputs, dummyOptions, None)

    def test_require_root_failed(self):
        #XXX: make root fail
        NetTest(StringIO(net_test_root_required),
                dummyInputs, dummyOptions, None)

    #def test_create_report_succeed(self):
    #    pass

    #def test_create_report_failed(self):
    #    pass

    #def test_run_all_test(self):
    #    raise NotImplementedError

    #def test_resume_test(self):
    #    pass

    #def test_progress(self):
    #    pass

    #def test_time_out(self):
    #    raise NotImplementedError

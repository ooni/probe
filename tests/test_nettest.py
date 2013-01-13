import os
from StringIO import StringIO
from tempfile import TemporaryFile, mkstemp

from twisted.trial import unittest
from twisted.internet import defer, reactor

from ooni.nettest import NetTest, InvalidOption, MissingRequiredOption
from ooni.nettest import FailureToLoadNetTest
from ooni.tasks import BaseTask
from ooni.utils import NotRootError

net_test_string = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham']]

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

net_test_string_with_file = """
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

net_test_with_required_option = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham'],
                     ['foo', 'o', None, 'moo'],
                     ['bar', 'o', None, 'baz'],
    ]

class DummyTestCase(NetTestCase):
    inputFile = ['file', 'f', None, 'The input File']

    usageOptions = UsageOptions

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'

    requiredOptions = ['foo', 'bar']
"""

dummyInputs = range(1)
dummyOptions = {'spam': 'notham'}
dummyInvalidOptions = {'cram': 'jam'}
dummyOptionsWithRequiredOptions = {'foo':'moo', 'bar':'baz'}

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
        NetTest.__init__(self, StringIO(net_test_string), dummyOptions)
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
    def setUp(self):
        with open('dummyInputFile.txt', 'w') as f:
            for i in range(10):
                f.write("%s\n" % i)

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

        net_test_from_file = NetTest(net_test_file,
                dummyOptions, DummyReporter())

        test_methods = set()
        for test_class, test_method in net_test_from_file.test_cases:
            instance = test_class()
            c = getattr(instance, test_method)
            self.assertCallable(c)

            test_methods.add(test_method)

        self.assertEqual(set(['test_a', 'test_b']), test_methods)

        os.unlink(net_test_file)

    def test_load_net_test_from_str(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        net_test_from_string = NetTest(net_test_string,
                dummyOptions, DummyReporter())

        test_methods = set()
        for test_class, test_method in net_test_from_string.test_cases:
            instance = test_class()
            c = getattr(instance, test_method)
            self.assertCallable(c)

            test_methods.add(test_method)

        self.assertEqual(set(['test_a', 'test_b']), test_methods)

    def test_load_net_test_from_StringIO(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        net_test_from_string = NetTest(StringIO(net_test_string),
                dummyOptions, DummyReporter())

        test_methods = set()
        for test_class, test_method in net_test_from_string.test_cases:
            instance = test_class()
            c = getattr(instance, test_method)
            self.assertCallable(c)

            test_methods.add(test_method)

        self.assertEqual(set(['test_a', 'test_b']), test_methods)

    def test_load_with_option(self):
        net_test = NetTest(StringIO(net_test_string),
                dummyOptions, None)
        self.assertIsInstance(net_test, NetTest)
        for test_klass, test_meth in net_test.test_cases:
            for option in dummyOptions.keys():
                self.assertIn(option, test_klass.usageOptions())

    def test_load_with_invalid_option(self):
        try:
            NetTest(StringIO(net_test_string), dummyInvalidOptions, None)
        except InvalidOption:
            pass

    def test_load_with_required_option(self):
        self.assertIsInstance(NetTest(StringIO(net_test_with_required_option),
                dummyOptionsWithRequiredOptions, None), NetTest)

    def test_load_with_missing_required_option(self):
        try:
            NetTest(StringIO(net_test_with_required_option),
                    dummyOptions, None)
        except MissingRequiredOption:
            pass

    def test_net_test_inputs(self):
        dummyOptionsWithFile = dict(dummyOptions)
        dummyOptionsWithFile['file'] = 'dummyInputFile.txt'

        net_test = NetTest(StringIO(net_test_string_with_file),
            dummyOptionsWithFile, None)

        for test_class, test_method in net_test.test_cases:
            self.assertEqual(len(list(test_class.inputs)), 10)

    def test_setup_local_options_in_test_cases(self):
        net_test = NetTest(StringIO(net_test_string),
            dummyOptions, None)

        for test_class, test_method in net_test.test_cases:
            self.assertEqual(test_class.localOptions, dummyOptions)

    def test_generate_measurements_size(self):
        dummyOptionsWithFile = dict(dummyOptions)
        dummyOptionsWithFile['file'] = 'dummyInputFile.txt'

        net_test = NetTest(StringIO(net_test_string_with_file),
            dummyOptionsWithFile, None)

        measurements = list(net_test.generateMeasurements())
        self.assertEqual(len(measurements), 20)

    #def test_require_root_succeed(self):
    #    #XXX: will require root to run
    #    n = NetTest(StringIO(net_test_root_required),
    #            dummyOptions, None)
    #    for test_class, method in n.test_cases:
    #        self.assertTrue(test_class.requiresRoot)

    def test_require_root_failed(self):
        #XXX: will fail if you run as root
        try:
            NetTest(StringIO(net_test_root_required),
                    dummyOptions, None)
        except NotRootError:
            pass

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

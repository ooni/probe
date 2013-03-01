import os
from StringIO import StringIO
from tempfile import TemporaryFile, mkstemp

from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.python.usage import UsageError

from ooni.nettest import NetTest, InvalidOption, MissingRequiredOption
from ooni.nettest import NetTestLoader, FailureToLoadNetTest
from ooni.tasks import BaseTask
from ooni.utils import NotRootError

from ooni.director import Director

from ooni.managers import TaskManager

from tests.mocks import MockMeasurement, MockMeasurementFailOnce
from tests.mocks import MockNetTest, MockDirector, MockReporter
from tests.mocks import MockMeasurementManager
defer.setDebugging(True)

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
dummyArgs = ('--spam', 'notham')
dummyOptions = {'spam':'notham'}
dummyInvalidArgs = ('--cram', 'jam')
dummyInvalidOptions= {'cram':'jam'}
dummyArgsWithRequiredOptions = ('--foo', 'moo', '--bar', 'baz')
dummyRequiredOptions = {'foo':'moo', 'bar':'baz'}
dummyArgsWithFile = ('--spam', 'notham', '--file', 'dummyInputFile.txt')

class TestNetTest(unittest.TestCase):
    timeout = 1
    def setUp(self):
        with open('dummyInputFile.txt', 'w') as f:
            for i in range(10):
                f.write("%s\n" % i)

    def assertCallable(self, thing):
        self.assertIn('__call__', dir(thing))

    def verifyMethods(self, testCases):
        uniq_test_methods = set()
        for test_class, test_methods in testCases:
            instance = test_class()
            for test_method in test_methods:
                c = getattr(instance, test_method)
                self.assertCallable(c)
                uniq_test_methods.add(test_method)
        self.assertEqual(set(['test_a', 'test_b']), uniq_test_methods)

    def test_load_net_test_from_file(self):
        """
        Given a file verify that the net test cases are properly
        generated.
        """
        __, net_test_file = mkstemp()
        with open(net_test_file, 'w') as f:
            f.write(net_test_string)
        f.close()

        options = {'subargs':dummyArgs, 'test':net_test_file}
        ntl = NetTestLoader(options)
        self.verifyMethods(ntl.testCases)
        os.unlink(net_test_file)

    def test_load_net_test_from_str(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        options = {'subargs':dummyArgs, 'test':net_test_string}
        ntl = NetTestLoader(options)
        self.verifyMethods(ntl.testCases)

    def test_load_net_test_from_StringIO(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        options = {'subargs':dummyArgs, 'test':StringIO(net_test_string)}
        ntl = NetTestLoader(options)
        self.verifyMethods(ntl.testCases)

    def test_load_with_option(self):
        options = {'subargs':dummyArgs, 'test':StringIO(net_test_string)}
        ntl = NetTestLoader(options)
        self.assertIsInstance(ntl, NetTestLoader)
        for test_klass, test_meth in ntl.testCases:
            for option in dummyOptions.keys():
                self.assertIn(option, test_klass.usageOptions())

    def test_load_with_invalid_option(self):
        options = {'subargs':dummyInvalidArgs,
            'test':StringIO(net_test_string)}
        try:
            ntl = NetTestLoader(options)
            ntl.checkOptions()
            raise Exception
        except UsageError:
            pass

    def test_load_with_required_option(self):
        options = {'subargs':dummyArgsWithRequiredOptions,
            'test':StringIO(net_test_with_required_option)}
        net_test = NetTestLoader(options)
        self.assertIsInstance(net_test, NetTestLoader)

    def test_load_with_missing_required_option(self):
        options = {'subargs':dummyArgs,
            'test':StringIO(net_test_with_required_option)}
        try:
            net_test = NetTestLoader(options)
        except MissingRequiredOption:
            pass

    def test_net_test_inputs(self):
        options = {'subargs':dummyArgsWithFile,
            'test':StringIO(net_test_string_with_file)}
        ntl = NetTestLoader(options)
        ntl.checkOptions()

        # XXX: if you use the same test_class twice you will have consumed all
        # of its inputs!
        tested = set([])
        for test_class, test_method in ntl.testCases:
            if test_class not in tested:
                tested.update([test_class])
                self.assertEqual(len(list(test_class.inputs)), 10)

    def test_setup_local_options_in_test_cases(self):
        options = {'subargs':dummyArgs, 'test':StringIO(net_test_string)}
        ntl = NetTestLoader(options)
        ntl.checkOptions()

        for test_class, test_method in ntl.testCases:
            self.assertEqual(test_class.localOptions, dummyOptions)

    def test_generate_measurements_size(self):

        options = {'subargs':dummyArgsWithFile,
            'test':StringIO(net_test_string_with_file)}
        ntl = NetTestLoader(options)
        ntl.checkOptions()
        net_test = NetTest(ntl, None)

        measurements = list(net_test.generateMeasurements())
        self.assertEqual(len(measurements), 20)

    def test_net_test_completed_callback(self):
        options = {'subargs':dummyArgsWithFile,
            'test':StringIO(net_test_string_with_file)}
        ntl = NetTestLoader(options)
        ntl.checkOptions()
        director = Director()

        d = director.startNetTest('', ntl, [MockReporter()])

        @d.addCallback
        def complete(result):
            #XXX: why is the return type (True, None) ?
            self.assertEqual(result, [(True,None)])
            self.assertEqual(director.successfulMeasurements, 20)

        return d

    def test_require_root_succeed(self):
        #XXX: will require root to run
        options = {'subargs':dummyArgs,
            'test':StringIO(net_test_root_required)}
        ntl = NetTestLoader(options)
        for test_class, method in ntl.testCases:
            self.assertTrue(test_class.requiresRoot)

    #def test_require_root_failed(self):
    #    #XXX: will fail if you run as root
    #    try:
    #        net_test = NetTestLoader(StringIO(net_test_root_required),
    #                dummyArgs)
    #    except NotRootError:
    #        pass

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

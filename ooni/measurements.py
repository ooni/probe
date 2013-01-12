from .tasks import TaskWithTimeout
from inspect import getmembers
from ooni.nettest import NetTestCase
from ooni.ratelimiting import StaticRateLimiter
from twisted.python.reflect import prefixedMethodNames
from twisted.trial.runner import filenameToModule
from StringIO import StringIO
from os.path import isfile

class Measurement(TaskWithTimeout):
    def __init__(self, test_class, test_method, test_input, net_test):
        """
        test_class:
            is the class, subclass of NetTestCase, of the test to be run

        test_method:
            is a string representing the test method to be called to perform
            this measurement

        test_input:
            is the input to the test
        """
        self.test_instance = test_class()
        self.test_instance.input = test_input
        self.test_instance.report = {}
        self.test_instance._start_time = time.time()
        self.test_instance._setUp()
        self.test_instance.setUp()
        self.test = getattr(self.test_instance, test_method)

    def succeeded(self):
        self.net_test.measurementSuccess()

    def failed(self):
        self.net_test.measurementFailed()

    def timedOut(self):
        self.net_test.measurementTimeOut()

    def run(self):
        d = defer.maybeDeferred(self.test)
        d.addCallback(self.succeeded)
        d.addErrback(self.failed)
        return d

class NetTest(object):
    director = None
    method_prefix = 'test'

    def __init__(self, net_test_file, inputs, options, report):
        """
        net_test_file:
            is a file object containing the test to be run.

        inputs:
            is a generator containing the inputs to the net test.

        options:
            is a dict containing the options to be passed to the net test.
        """
        self.test_cases = self.loadNetTest(net_test_file)
        self.inputs = inputs
        self.options = options

    def loadNetTest(self, net_test_object):
        """
        Creates all the necessary test_cases (a list of tuples containing the
        NetTestCase (test_class, test_method))

        example:
            [(test_classA, test_method1),
            (test_classA, test_method2),
            (test_classA, test_method3),
            (test_classA, test_method4),
            (test_classA, test_method5),

            (test_classB, test_method1),
            (test_classB, test_method2)]

        Note: the inputs must be valid for test_classA and test_classB.

        net_test_object:
            is a file like object that will be used to generate the test_cases.
        """
        try:
            if isfile(net_test_object):
                return self._loadNetTestFile(net_test_object)
        except TypeError:
            if isinstance(net_test_object, StringIO) or \
                isinstance(net_test_object, str):
                return self._loadNetTestString(net_test_object)

    def _loadNetTestString(self, net_test_string):
        """
        Load NetTest from a string
        """
        ns = {}
        test_cases = []
        exec net_test_string.read() in ns
        for item in ns.itervalues():
            test_cases.extend(self._get_test_methods(item))
        return test_cases

    def _loadNetTestFile(self, net_test_file):
        """
        Load NetTest from a file
        """
        test_cases = []
        module = filenameToModule(net_test_file)
        for __, item in getmembers(module):
            test_cases.extend(self._get_test_methods(item))
        return test_cases

    def _get_test_methods(self, item):
        """
        Look for test_ methods in subclasses of NetTestCase
        """
        test_cases = []
        try:
            assert issubclass(item, NetTestCase)
            methods = prefixedMethodNames(item, self.method_prefix)
            for method in methods:
                test_cases.append((item, self.method_prefix + method))
        except (TypeError, AssertionError):
            pass
        return test_cases

    def timedOut(self, measurement):
        """
        This gets called when a measurement has timed out. This may or may not
        trigger a retry inside of MeasurementsTracker.
        """
        self.director.measurementTimedOut(measurement)

    def failed(self, measurement, failure):
        """
        This gets called when a measurement has failed in the sense that all
        the retries have failed at successfully running the test.
        This means that it's a definitive failure and we will no longer make
        any attempts at re-running the measurement.
        """
        self.director.measurementFailed(measurement, failure)

    def succeeded(self, measurement):
        """
        This gets called when a measurement has failed.
        """
        self.report.write(measurement)

    def generateMeasurements(self):
        """
        This is a generator that yields measurements and sets their timeout
        value and their netTest attribute.
        """
        for test_input in self.inputs:
            for test_class, test_method in self.test_cases:
                measurement = Measurement(test_class, test_method, test_input)
                measurement.netTest = self
                measurement.timeout = self.rateLimiter.timeout
                yield measurement


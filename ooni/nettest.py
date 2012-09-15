
from twisted.python import log
from twisted.trial import unittest, itrial

pyunit = __import__('unittest')

def _iterateTests(testSuiteOrCase):
    """
    Iterate through all of the test cases in C{testSuiteOrCase}.
    """
    try:
        suite = iter(testSuiteOrCase)
    except TypeError:
        yield testSuiteOrCase
    else:
        for test in suite:
            for subtest in _iterateTests(test):
                yield subtest


class TestCase(unittest.TestCase):
    """
    A test case represents the minimum
    """
    def run(self, result):
        """
        Run the test case, storing the results in C{result}.

        First runs C{setUp} on self, then runs the test method (defined in the
        constructor), then runs C{tearDown}.  As with the standard library
        L{unittest.TestCase}, the return value of these methods is disregarded.
        In particular, returning a L{Deferred} has no special additional
        consequences.

        @param result: A L{TestResult} object.
        """
        log.msg("--> %s <--" % (self.id()))
        new_result = itrial.IReporter(result, None)
        if new_result is None:
            result = PyUnitResultAdapter(result)
        else:
            result = new_result
        result.startTest(self)
        if self.getSkip(): # don't run test methods that are marked as .skip
            result.addSkip(self, self.getSkip())
            result.stopTest(self)
            return

        self._passed = False
        self._warnings = []

        self._installObserver()
        # All the code inside _runFixturesAndTest will be run such that warnings
        # emitted by it will be collected and retrievable by flushWarnings.
        unittest._collectWarnings(self._warnings.append, self._runFixturesAndTest, result)

        # Any collected warnings which the test method didn't flush get
        # re-emitted so they'll be logged or show up on stdout or whatever.
        for w in self.flushWarnings():
            try:
                warnings.warn_explicit(**w)
            except:
                result.addError(self, failure.Failure())

        result.stopTest(self)


class TestSuite(pyunit.TestSuite):
    """
    Extend the standard library's C{TestSuite} with support for the visitor
    pattern and a consistently overrideable C{run} method.
    """

    def __init__(self, tests=(), inputs=()):
        self._tests = []
        self._inputs = []
        self.addTests(tests, inputs)
        print "Adding %s %s" % (tests, inputs)


    def __call__(self, result):
        return self.run(result)

    def __repr__(self):
        return "<%s input=%s tests=%s>" % (self.__class__,
                self._inputs, list(self))

    def run(self, result, input=None):
        """
        Call C{run} on every member of the suite.
        """
        for test in self._tests:
            if result.shouldStop:
                break
            return test(result, None)

    def addTests(self, tests, inputs=[]):
        if isinstance(tests, basestring):
            raise TypeError("tests must be and iterable of tests not a string")
        for test in tests:
            self.addTest(test, inputs)

    def addTest(self, test, inputs=[]):
        #print "Adding: %s" % test
        super(TestSuite, self).addTest(test)
        self._inputs = inputs



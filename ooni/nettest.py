
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


class TestSuite(pyunit.TestSuite):
    inputUnit = [None]
    def __repr__(self):
        return "<%s input=%s, tests=%s>" % (self.__class__, self.inputUnit, list(self))

    def run(self, result, inputUnit=[None]):
        """
        Call C{run} on every member of the suite.
        """
        # we implement this because Python 2.3 unittest defines this code
        # in __call__, whereas 2.4 defines the code in run.
        idx = 0
        for input, test in itertools.product(inputUnit, self._tests):
            if result.shouldStop:
                break
            self.inputUnit = inputUnit
            test.input = input
            test.idx = idx
            test(result)
            idx += 1

        return result

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



import itertools

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


class TestSuiteFactory(object):
    def __init__(self, inputUnit, tests, basesuite):
        self._baseSuite = basesuite
        self._inputUnit = inputUnit
        self._idx = 0
        self.tests = tests

    def __iter__(self):
        return self

    def next(self):
        try:
            next_input = self._inputUnit.next()
            print "Now dealing with %s %s" % (next_input, self._idx)
        except:
            raise StopIteration
        new_test_suite = self._baseSuite(self.tests)
        new_test_suite.input = next_input
        new_test_suite._idx = self._idx

        self._idx += 1
        return new_test_suite

class TestSuite(pyunit.TestSuite):
    def __init__(self, tests=()):
        self._tests = []
        self.input = None
        self._idx = 0
        self.addTests(tests)

    def __repr__(self):
        return "<%s input=%s tests=%s>" % (self.__class__,
                self.input, self._tests)

    def run(self, result):
        """
        Call C{run} on every member of the suite.
        """
        # we implement this because Python 2.3 unittest defines this code
        # in __call__, whereas 2.4 defines the code in run.
        for i, test in enumerate(self._tests):
            if result.shouldStop:
                break
            test.input = self.input
            test._idx = self._idx + i
            test(result)

        return result

class TestCase(unittest.TestCase):
    name = "DefaultTestName"
    inputs = [None]

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)



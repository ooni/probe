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
    name = "DefaultTestName"

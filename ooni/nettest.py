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

class InputTestSuite(pyunit.TestSuite):
    def run(self, result, idx=0):
        self._idx = idx
        while self._tests:
            if result.shouldStop:
                break
            test = self._tests.pop(0)
            try:
                test.input = self.input
                test._idx = self._idx
                print "IDX: %s" % self._idx
                test(result)
            except:
                test(result)
            self._idx += 1
        return result

class TestCase(unittest.TestCase):
    name = "DefaultTestName"
    inputs = []

    def getOptions(self):
        return {'inputs': self.inputs}

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)



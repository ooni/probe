import itertools
from twisted.python import log
from twisted.trial import unittest, itrial

pyunit = __import__('unittest')

class InputTestSuite(pyunit.TestSuite):
    """
    This in an extension of a unittest test suite. It adds support for inputs
    and the tracking of current index via idx.
    """
    def run(self, result, idx=0):
        self._idx = idx
        while self._tests:
            if result.shouldStop:
                break
            test = self._tests.pop(0)
            try:
                test.input = self.input
                test._idx = self._idx
                test(result)
            except:
                test(result)
            self._idx += 1
        return result

class TestCase(unittest.TestCase):
    name = "DefaultOONITestCase"
    inputs = [None]

    def getOptions(self):
        return {'inputs': self.inputs}

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)



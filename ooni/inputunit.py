from twisted.trial import unittest

class PatchedPyUnitResultAdapter(unittest.PyUnitResultAdapter):
    def __init__(self, original):
        """
        Here we patch PyUnitResultAdapter to support our reporterFactory to
        properly write headers to reports.
        """
        self.original = original
        self.reporterFactory = original.reporterFactory

unittest.PyUnitResultAdapter = PatchedPyUnitResultAdapter

class InputUnitFactory(object):
    """
    This is a factory that takes the size of input units to be generated a set
    of units that is a python iterable item and outputs InputUnit objects
    containing inputUnitSize elements.

    This object is a python iterable, this means that it does not need to keep
    all the elements in memory to be able to produce InputUnits.
    """
    inputUnitSize = 10
    def __init__(self, inputs=[]):
        self._inputs = iter(inputs)
        self._idx = 0
        self._ended = False

    def __iter__(self):
        return self

    def next(self):
        input_unit_elements = []

        if self._ended:
            raise StopIteration

        for i in xrange(self._idx, self._idx + self.inputUnitSize):
            try:
                input_unit_elements.append(self._inputs.next())
            except:
                self._ended = True
                break
        self._idx += self.inputUnitSize

        if not input_unit_elements:
            raise StopIteration

        return InputUnit(input_unit_elements)


class InputUnit(object):
    """
    This is a python iterable object that contains the input elements to be
    passed onto a TestCase.
    """
    def __init__(self, inputs=[]):
        self._inputs = iter(inputs)

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self._inputs)

    def __add__(self, inputs):
        for input in inputs:
            self._inputs.append(input)

    def __iter__(self):
        return self

    def next(self):
        try:
            return self._inputs.next()
        except:
            raise StopIteration

    def append(self, input):
        self._inputs.append(input)




class InputUnitFactory(object):
    """
    This is a factory that takes the size of input units to be generated a set
    of units that is a python iterable item and outputs InputUnit objects
    containing inputUnitSize elements.

    This object is a python iterable, this means that it does not need to keep
    all the elements in memory to be able to produce InputUnits.
    """
    inputUnitSize = 3
    def __init__(self, inputs=[]):
        self._inputs = inputs
        self._idx = 0
        self._ended = False

    def __iter__(self):
        return self

    def next(self):
        if self._ended:
            raise StopIteration

        last_element_idx = self._idx + self.inputUnitSize
        input_unit_elements = self._inputs[self._idx:last_element_idx]
        try:
            # XXX hack to fail when we reach the end of the list
            antani = self._inputs[last_element_idx]
        except:
            if len(input_unit_elements) > 0:
                self._ended = True
                return InputUnit(input_unit_elements)
            else:
                raise StopIteration

        self._idx += self.inputUnitSize

        return InputUnit(input_unit_elements)


class InputUnit(object):
    """
    This is a python iterable object that contains the input elements to be
    passed onto a TestCase.
    """
    def __init__(self, inputs=[]):
        self._inputs = inputs

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self._inputs)

    def __add__(self, inputs):
        for input in inputs:
            self._inputs.append(input)

    def __iter__(self):
        return iter(self._inputs)

    def append(self, input):
        self._inputs.append(input)




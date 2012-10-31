# -*- coding: utf-8 -*-
#
# inputunit.py
# ------------
# Classes and function for working with OONI TestCase inputs.
#
# @authors: Arturo Filasto, Isis Lovecruft
# @version: 0.1.0-alpha
# @license: see included LICENSE file
# @copyright: 2012 Arturo Filasto, Isis Lovecruft, The Tor Project Inc.
#

from twisted.trial import unittest

from zope.interface.exceptions import BrokenImplementation


def simpleInputUnitProcessor(input_unit):
    """A simple InputUnit generator without parsing."""
    try:
        assert hasattr(input_unit, '__iter__'), "inputs must be iterable!"
    except AssertionError, ae:
        raise BrokenImplementation, ae
    else:
        for i in input_unit:
            yield i


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
    This is a factory that takes the size of input units to be generated and a
    set of units that is a python iterable item, and outputs InputUnit objects
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

class IUProcessorExit(GeneratorExit):
    """InputUnitProcessor has exited."""

class IUProcessorAborted(Exception):
    """The InputUnitProcessor was aborted with Inputs remaining."""

class InputUnitProcessor(InputUnit):
    """
    Create a generator for returning inputs one-by-one from a
    :class:`InputUnit` (or any other iterable defined within an instance of
    :class:`ooni.nettest.TestCase`), and a generator function.

    The :ivar:generator can be a custom generator, or chain of generators, for
    customized parsing of an InputUnit, or it can be an imported
    function. There are useful imported functions in the builtin
    :mod:`itertools`. If no :ivar:`generator` is given, the default one strips
    whitespace characters, then returns the Input if the input does not begin
    with a crunch (#) or bang (!). :)

    If :ivar:catchStopIter is True, then catch any StopIterations and return a
    2-tuple containing (boolean, list(unprocessed)):

        (True, None) when :ivar:iterable is empty, or
        (False, [unprocessed]) if :ivar:iterable was not empty.

    If :ivar:catchStopIter is False (default), then we catch the StopIteration
    exception, mark :attr:`empty` as 'True', and reraise the StopIteration.

    xxx fill me in with parameter details
    """
    empty = False

    def __init__(self, iterable, input_filter=None, catch_err=False):
        """
        Create an InputUnitProcessor.

        xxx fill me in
        """
        from itertools import takewhile
        from types     import GeneratorType

        assert hasattr(iterable, "__iter__"), "That's not an iterable!"

        self._iterable = iterable
        self._infilter = input_filter
        self._noerr    = catch_err
        self._empty    = self.empty

    def __len__(self):
        return len(self.iterable)

    def __unprocessed__(self):
        if not self.isdone():
            unprocessed = \
                [u for u in self._unit if self._unit is not StopIteration]
            return (False, unprocessed)
        else:
            return (True, None)

    def isdone(self):
        return self._empty

    def throw(self, exception, message="", traceback=None):
        try:
            raise exception, message, traceback
        except:
            yield self._iterable.next()

    @staticmethod
    def __strip__(x):
        return x.strip()

    @staticmethod
    def _default_input_filter(x):
        if not x.startswith('#') and not x.startswith('!'):
            return True
        else:
            return False

    def __make_filter__(self):
        if self.input_filter and hasattr(self.input_filter, "__call__"):
            return self.input_filter
        else:
            return self._default_input_filter

    def finish(self):
        if self._noerr:
            return self.__unprocessed__()
        else:
            if not self.isdone():
                raise IUProcessorAborted
            else:
                raise IUProcessorExit

    def process(self):
        carbon = self.__make_filter__()
        try:
            yield takewhile(carbon,
                            [i for i in self.__strip__(self._iterable)]
                            ).next()
        except StopIteration, si:
            self._empty = True
            yield self.finish()

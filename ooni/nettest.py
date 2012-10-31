# -*- coding: utf-8 -*-

import itertools
import os

from inspect                   import classify_class_attrs
from pprint                    import pprint

from twisted.internet          import defer, utils
from twisted.python            import usage
from twisted.trial             import unittest, itrial
from zope.interface.exceptions import BrokenImplementation

from ooni.inputunit            import InputUnitProcessor
from ooni.utils                import log
from ooni.utils.assertions     import isClass, isNotClass
from ooni.utils.assertions     import isOldStyleClass, isNewStyleClass


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
    """
    This is the monad of the OONI nettest universe. When you write a nettest
    you will subclass this object.

    * inputs: can be set to a static set of inputs. All the tests (the methods
      starting with the "test_" prefix) will be run once per input.  At every
      run the _input_ attribute of the TestCase instance will be set to the
      value of the current iteration over inputs.  Any python iterable object
      can be set to inputs.

    * inputFile: attribute should be set to an array containing the command
      line argument that should be used as the input file. Such array looks
      like this:

          ``["commandlinearg", "c", "The description"]``

      The second value of such arrray is the shorthand for the command line
      arg.  The user will then be able to specify inputs to the test via:

          ``ooniprobe mytest.py --commandlinearg path/to/file.txt``

      or

          ``ooniprobe mytest.py -c path/to/file.txt``


    * inputProcessor: should be set to a function that takes as argument an
      open file descriptor and it will yield the input to be passed to the
      test instance.

    * name: should be set to the name of the test.

    * author: should contain the name and contact details for the test author.
      The format for such string is as follows:

          ``The Name <email@example.com>``

    * version: is the version string of the test.
    """
    name    = "I Did Not Change The Name"
    author  = "John Doe <foo@example.com>"
    version = "0.0.0"

    inputFile = None
    inputs    = [None]

    report = {}
    report['errors'] = []

    optParameters = None
    optFlags      = None
    subCommands   = None

    def setUpClass(self, *args, **kwargs):
        """
        Create a TestCase instance. This function is equivalent to '__init__'.
        To add futher setup steps before a set of tests in a TestCase instance
        run, create a function called 'setUp'.

        Class attributes, such as `report`, `optParameters`, `name`, and
        `author` should be overriden statically as class attributes in any
        subclass of :class:`ooni.nettest.TestCase`, so that the calling
        functions in ooni.runner can handle them correctly.
        """
        methodName = 'runTest'
        if kwargs:
            if 'methodName' in kwargs:
                methodName = kwargs['methodName']

        super(TestCase, self).__init__(methodName=methodName)

        #for key, value in kwargs.items():
        #    setattr(self.__class__, key, value)
        #
        #self.inputs = self.getInputs()

    def deferSetUp(self, ignored, result):
        """
        If we have the reporterFactory set we need to write the header. If
        such method is not present we will only run the test skipping header
        writing.
        """
        if result.reporterFactory.firstrun:
            d1 = result.reporterFactory.writeHeader()
            d2 = unittest.TestCase.deferSetUp(self, ignored, result)
            dl = defer.DeferredList([d1, d2])
            return dl
        else:
            return unittest.TestCase.deferSetUp(self, ignored, result)

    def _raaun(self, methodName, result):
        from twisted.internet import reactor
        method = getattr(self, methodName)
        log.debug("Running %s" % methodName)
        d = defer.maybeDeferred(
                utils.runWithWarningsSuppressed, self._getSuppress(), method)
        d.addBoth(lambda x : call.active() and call.cancel() or x)
        return d

    @staticmethod
    def inputParser(inputs):
        """Replace me with a custom function for parsing inputs."""
        return inputs

    def __input_file_processor__(self, fp):
        """
        I open :attr:inputFile if there is one, and return inputs one by one
        after stripping them of whitespace and running them through the parser
        :meth:`inputParser`.
        """
        for line in fp.readlines():
            yield self.inputParser(line.strip())
        fp.close()

    def __get_inputs__(self):
        """
        I am called from the ooni.runner and you probably should not override
        me. I gather the internal inputs from an instantiated test class and
        pass them to the rest of the runner.

        If you are looking for a way to parse inputs from inputFile, see
        :meth:`inputParser`.
        """
        processor = InputUnitProcessor(self.inputs,
                                       input_filter=None,
                                       catch_err=False)
        processed = processor.process()

        log.msg("Received direct inputs:\n%s" % inputs)
        log.debug("Our InputUnitProcessor is %s" % processor)

        #while processed is not StopIteration:
        #    self.inputs = processed
        #    yield self.inputs
        #else:
        #    if self.inputFile:

        if self.inputFile:
            try:
                fp = open(self.inputFile) ## xxx fixme:
            except Exception, e:          ## bad news to leave file
                log.err(e)                ## descriptors open
            else:
                from_file = self.__input_file_processor__(fp)
                self.inputs = itertools.chain(processor, from_file)
        elif self.inputFile is False:
            log.debug("%s specified that it doesn't need inputFile."
                      % self.__class__.__name__)
            self.inputs = processed
        else:
            raise BrokenImplementation

        return self.inputs

    def getOptions(self):
        '''
        for attr in attributes:
            if not attr.name is 'optParameters' or attr.name is 'optFlags':
                continue
            elif attr.name is 'optParameters':
                cls._optParameters = attr.object
            elif attr.name is 'optFlags':
                log.debug("Applying %s.%s = %s to data descriptor..."
                          % (cls.__name__, "_"+attr.name, attr.object))
                cls._optParameters = attr.object
            else:
                log.debug("How did we get here? attr.name = %s" % attr.name)
        '''
        if self.localOptions:
            if self.inputs[0] is not None or self.inputFile is not None:
                self.__get_inputs__()
            return self.localOptions
        else:
            raise Exception, "could not find cls.localOptions! 234"

        # if options:
        #     return options
        # else:
        #     ## is this safe to do? it might turn Hofstaeder...
        #     return self.__dict__
        ####################
        ## original return
        ####################
        #return {'inputs': self.inputs,
        #        'name': self.name,
        #        'version': self.version}

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)


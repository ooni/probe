# -*- coding: utf-8 -*-

import itertools
import os

from twisted.trial import unittest, itrial, util
from twisted.internet import defer, utils
from ooni.utils import log

pyunit = __import__('unittest')

class InputTestSuite(pyunit.TestSuite):
    """
    This in an extension of a unittest test suite. It adds support for inputs
    and the tracking of current index via idx.
    """
    def run(self, result, idx=0):
        log.debug("Running test suite")
        self._idx = idx
        while self._tests:
            if result.shouldStop:
                log.debug("Detected that test should stop")
                log.debug("Stopping...")
                break
            test = self._tests.pop(0)

            try:
                log.debug("Setting test attributes with %s %s" %
                            (self.input, self._idx))

                test.input = self.input
                test._idx = self._idx
            except Exception, e:
                log.debug("Error in some stuff")
                log.debug(e)
                import sys
                print sys.exc_info()

            try:
                log.debug("Running test")
                test(result)
                log.debug("Ran.")
            except Exception, e:
                log.debug("Attribute error thing")
                log.debug("Had some problems with _idx")
                log.debug(e)
                import traceback, sys
                print sys.exc_info()
                traceback.print_exc()
                print e

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
            log.debug("Detecting first run. Writing report header.")
            d1 = result.reporterFactory.writeHeader()
            d2 = unittest.TestCase.deferSetUp(self, ignored, result)
            dl = defer.DeferredList([d1, d2])
            return dl
        else:
            log.debug("Not first run. Running test setup directly")
            return unittest.TestCase.deferSetUp(self, ignored, result)

    def inputProcessor(self, fp):
        log.debug("Running default input processor")
        for x in fp.readlines():
            yield x.strip()
        fp.close()

    def getOptions(self):
        log.debug("Getting options for test")
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


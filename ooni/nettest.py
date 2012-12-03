# -*- encoding: utf-8 -*-
#
# nettest.py
# ----------
# In here is the NetTest API definition. This is how people
# interested in writing ooniprobe tests will be specifying them
#
# :authors: Arturo Filastò, Isis Lovecruft
# :license: see included LICENSE file

import sys
import os
import itertools
import traceback

from twisted.trial import unittest, itrial
from twisted.trial import util as txtrutil
from twisted.internet import defer, utils
from twisted.python import usage

from ooni import runner
from ooni.utils import log

# This needs to be here so that NetTestCase.abort() can call it, since we
# cannot import runner because runner imports NetTestCase.
def isTestCase(obj):
    """
    Return True if obj is a subclass of NetTestCase, false if otherwise.
    """
    try:
        return issubclass(obj, NetTestCase)
    except TypeError:
        return False


class NetTestCase(object):
    """
    This is the base of the OONI nettest universe. When you write a nettest
    you will subclass this object.

    * inputs: can be set to a static set of inputs. All the tests (the methods
      starting with the "test" prefix) will be run once per input.  At every run
      the _input_ attribute of the TestCase instance will be set to the value of
      the current iteration over inputs.  Any python iterable object can be set
      to inputs.

    * inputFile: attribute should be set to an array containing the command line
      argument that should be used as the input file. Such array looks like
      this:

          ``["commandlinearg", "c", "default value" "The description"]``

      The second value of such arrray is the shorthand for the command line arg.
      The user will then be able to specify inputs to the test via:

          ``ooniprobe mytest.py --commandlinearg path/to/file.txt``

      or

          ``ooniprobe mytest.py -c path/to/file.txt``


    * inputProcessor: should be set to a function that takes as argument an
      open file descriptor and it will return the input to be passed to the test
      instance.

    * name: should be set to the name of the test.

    * author: should contain the name and contact details for the test author.
      The format for such string is as follows:

          ``The Name <email@example.com>``

    * version: is the version string of the test.

    * requiresRoot: set to True if the test must be run as root.

    * optFlags: 
          is assigned a list of lists. Each list represents a flag
          parameter, as so:

        optFlags = [
            ['verbose', 'v', 'Makes it tell you what it doing.'],
            ['quiet', 'q', 'Be vewy vewy quiet.']]

    As you can see, the first item is the long option name (prefixed with
    '--' on the command line), followed by the short option name (prefixed with
    '-'), and the description. The description is used for the built-in handling of
    the --help switch, which prints a usage summary.

    * optParameters: 
          is much the same, except the list also contains a default value:

        optParameters = [
            ['outfile', 'O', 'outfile.log', 'Description...']]

    * usageOptions: 
          a subclass of twisted.python.usage.Options for more advanced command
          line arguments fun.

    * requiredOptions: a list containing the name of the options that are
                       required for proper running of a test.

    * localOptions: contains the parsed command line arguments.

    Quirks:
    Every class that is prefixed with test *must* return a twisted.internet.defer.Deferred.
    """
    name = "I Did Not Change The Name"
    author = "Jane Doe <foo@example.com>"
    version = "0.0.0"

    inputs = [None]
    inputFile = None

    report = {}
    report['errors'] = []

    optFlags = None
    optParameters = None
    usageOptions = None
    requiredOptions = []
    requiresRoot = False

    localOptions = {}

    def _setUp(self):
        """This is the internal setup method to be overwritten by templates."""
        pass

    def setUp(self):
        """Place your logic to be executed when the test is being setup here."""
        pass

    def inputProcessor(self, filename=None):
        """
        You may replace this with your own custom input processor. It takes as
        input a file descriptor so remember to close it when you are done.

        This can be useful when you have some input data that is in a certain
        format and you want to set the input attribute of the test to something
        that you will be able to properly process.

        For example you may wish to have an input processor that will allow you
        to ignore comments in files. This can be easily achieved like so:

            fp = open(filename)
            for x in fp.xreadlines():
                if x.startswith("#"):
                    continue
                yield x.strip()
            fp.close()

        Other fun stuff is also possible.
        """
        log.debug("Running default input processor")
        if filename:
            fp = open(filename)
            for x in fp.xreadlines():
                yield x.strip()
            fp.close()
        else:
            pass

    def _checkRequiredOptions(self):
        for required_option in self.requiredOptions:
            log.debug("Checking if %s is present" % required_option)
            if not self.localOptions[required_option]:
                raise usage.UsageError("%s not specified!" % required_option)

    def _processOptions(self, options=None):
        if self.inputFile:
            self.inputs = self.inputProcessor(self.inputFile)

        self._checkRequiredOptions()

        # XXX perhaps we may want to name and version to be inside of a
        # different method that is not called options.
        return {'inputs': self.inputs,
                'name': self.name,
                'version': self.version}

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)

    def _getSkip(self):
        return txtrutil.acquireAttribute(self._parents, 'skip', None)

    #def _getSkipReason(self, method, skip):
    #    return super(TestCase, self)._getSkipReason(self, method, skip)

    def _getTimeout(self):
        """
        Returns the timeout value set on this test. Check on the instance
        first, the the class, then the module, then package. As soon as it
        finds something with a timeout attribute, returns that. Returns
        twisted.trial.util.DEFAULT_TIMEOUT_DURATION if it cannot find
        anything. See TestCase docstring for more details.
        """
        testMethod = getattr(self, methodName)
        self._parents = [testMethod, self]
        self._parents.extend(txtrutil.getPythonContainers(testMethod))
        timeout = txtrutil.acquireAttribute(self._parents, 'timeout', 
                                            txtrutil.DEFAULT_TIMEOUT_DURATION)
        try:
            return float(timeout)
        except (ValueError, TypeError):
            warnings.warn("'timeout' attribute needs to be a number.",
                          category=DeprecationWarning)
            return txtrutil.DEFAULT_TIMEOUT_DURATION

    def _abort(self, reason, obj=None):
        """
        Abort running an input, test_method, or test_class. If called with only
        one argument, assume we're going to ignore the current input. Otherwise,
        the name of the method or class in relation to the test_instance,
        i.e. "self" should be given as value for the keyword argument "obj".

        XXX call oreporter.allDone() from parent stack frame
        """
        reason = str(reason) # XXX should probably coerce
        raise SkipTest("%s\n%s" % (str(reason), str(self.input)) )

    def _abortMethod(self, reason, method):
        if inspect.ismethod(method):
            abort = getattr(self.__class__, method, False)
            log.debug("Aborting remaining inputs for %s" % str(abort.func_name))
            setattr(abort, 'skip', reason)
        else:
            log.debug("abortMethod(): could not find method %s" % str(method))

    @log.catch
    def _abortClass(self, reason, cls):
        if not inspect.isclass(obj) or not runner.isTestCase(obj):
            log.debug("_abortClass() could not find class %s" % str(cls))
            return
        abort = getattr(obj, '__class__', self.__class__)
        log.debug("Aborting %s test" % str(abort.name))
        setattr(abort, 'skip', reason)

    def abortCurrentInput(self, reason):
        """
        Abort the current input.
        
        @param reason: A string explaining why this test is being skipped.
        """
        return self._abort(reason)

    def abortInput(self, reason):
        return self._abort(reason)

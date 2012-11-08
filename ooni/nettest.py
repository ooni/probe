# -*- encoding: utf-8 -*-
#
#     nettest.py
# ------------------->
#
# :authors: Arturo "hellais" Filastò <art@fuffa.org>,
#           Isis Lovecruft <isis@torproject.org>
# :licence: see LICENSE
# :copyright: 2012 Arturo Filasto, Isis Lovecruft
# :version: 0.1.0-alpha
#
# <-------------------

import sys
import os
import itertools
import traceback

from twisted.trial import unittest, itrial, util
from twisted.internet import defer, utils
from twisted.python import usage

from ooni.utils import log

pyunit = __import__('unittest')

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

    * optFlags: is assigned a list of lists. Each list represents a flag parameter, as so:

        optFlags = [['verbose', 'v', 'Makes it tell you what it doing.'], | ['quiet', 'q', 'Be vewy vewy quiet.']]

    As you can see, the first item is the long option name (prefixed with
    '--' on the command line), followed by the short option name (prefixed with
    '-'), and the description. The description is used for the built-in handling of
    the --help switch, which prints a usage summary.


    * optParameters: is much the same, except the list also contains a default value:

        | optParameters = [['outfile', 'O', 'outfile.log', 'Description...']]

    * usageOptions: a subclass of twisted.python.usage.Options for more advanced command line arguments fun.

    * requiredOptions: a list containing the name of the options that are
                       required for proper running of a test.

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
    parallelism = 1

    def inputProcessor(self, fp):
        """
        You may replace this with your own custom input processor. It takes as
        input a file descriptor so remember to close it when you are done.

        This can be useful when you have some input data that is in a certain
        format and you want to set the input attribute of the test to something
        that you will be able to properly process.

        For example you may wish to have an input processor that will allow you
        to ignore comments in files. This can be easily achieved like so:

            for x in fp.xreadlines():
                if x.startswith("#"):
                    continue
                yield x.strip()
            fp.close()

        Other fun stuff is also possible.
        """
        log.debug("Running default input processor")
        for x in fp.xreadlines():
            yield x.strip()
        fp.close()

    def _processOptions(self, options=None):
        if self.inputFile:
            try:
                assert isinstance(self.inputFile, str)
            except AssertionError, ae:
                log.err(ae)
            else:
                if os.path.isfile(self.inputFile):
                    fp = open(self.inputFile)
                    self.inputs = self.inputProcessor(fp)
        elif not self.inputs[0]:
            pass
        elif self.inputFile:
            raise usage.UsageError("No input file specified!")

        # XXX this is a bit hackish
        if options:
            for required_option in self.requiredOptions:
                log.debug("Checking if %s is present" % required_option)
                if not options[required_option]:
                    raise usage.UsageError("%s not specified!" % required_option)

        # XXX perhaps we may want to name and version to be inside of a
        # different method that is not called options.
        return {'inputs': self.inputs,
                'name': self.name,
                'version': self.version}

    def __repr__(self):
        return "<%s inputs=%s>" % (self.__class__, self.inputs)


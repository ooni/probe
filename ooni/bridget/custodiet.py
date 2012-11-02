#!/usr/bin/env python
# -*- coding: UTF-8
#
#    custodiet
#    *********
#
#    "...quis custodiet ipsos custodes?"
#               - Juvenal, Satires VI.347-348 (circa 2nd Century, C.E.)
#
#        "'Hand me the Custodian,' Goodchild demands, inserting the waiflike
#    robot into Bambara's opened navel. 'Providing conscience for those who
#    have none.' Goodchild and the other Breen government agents disappear
#    into the surrounding desert in a vehicle, kicking up cloud of white dust.
#        Bambara awakens, and, patting the dust from his clothing, turns to
#    greet a one-armed child. 'Hi, my name's Bambara; I'm a
#    thirty-six-year-old Virgo and a former killer, who's hobbies include
#    performing recreational autopsies, defecating, and drinking rum. I've
#    recently been given a conscience, and would very much like to help you.'
#        Cut to Bambara and the child, now with one of Bambara's arms, leaving
#    a surgical clinic."
#               - AeonFlux, "The Purge" (sometime in the late 90s)
#
#    :copyright: (c) 2012 Isis Lovecruft
#    :license: see LICENSE for more details.
#    :version: 0.1.0-beta
#

# ooniprobe.py imports
import sys
from signal import SIGTERM, signal
from pprint import pprint

from twisted.python import usage
from twisted.internet import reactor
from twisted.plugin import getPlugins

from zope.interface.verify import verifyObject
from zope.interface.exceptions import BrokenImplementation
from zope.interface.exceptions import BrokenMethodImplementation

from ooni.bridget.tests import bridget
from ooni.bridget.utils import log, tests, work, reports
from ooni.bridget.utils.interface import ITest
from ooni.utils.logo import getlogo

# runner.py imports
import os
import types
import time
import inspect
import yaml

from twisted.internet import defer, reactor
from twisted.python   import reflect, failure, usage
from twisted.python   import log as tlog

from twisted.trial        import unittest
from twisted.trial.runner import TrialRunner, TestLoader
from twisted.trial.runner import isPackage, isTestCase, ErrorHolder
from twisted.trial.runner import filenameToModule, _importFromFile

from ooni              import nettest
from ooni.inputunit    import InputUnitFactory
from ooni.nettest      import InputTestSuite
from ooni.plugoo       import tests as oonitests
from ooni.reporter     import ReporterFactory
from ooni.utils        import log, geodata, date
from ooni.utils.legacy import LegacyOONITest
from ooni.utils.legacy import start_legacy_test, adapt_legacy_test


__version__ = "0.1.0-beta"


#def retrieve_plugoo():
#    """
#    Get all the plugins that implement the ITest interface and get the data
#    associated to them into a dict.
#    """
#    interface = ITest
#    d = {}
#    error = False
#    for p in getPlugins(interface, plugins):
#        try:
#            verifyObject(interface, p)
#            d[p.shortName] = p
#        except BrokenImplementation, bi:
#            print "Plugin Broken"
#            print bi
#            error = True
#    if error != False:
#        print "Plugin Loaded!"
#    return d
#
#plugoo = retrieve_plugoo()

"""

ai to watch over which tests to run - custodiet

   * runTest() or getPrefixMethodNames() to run the tests in order for each
     test (esp. the tcp and icmp parts) to be oonicompat we should use the
     test_icmp_ping API framework for those.

   * should handle calling

tests to run:
  echo
  syn
  fin
  conn
  tls
  tor
need fakebridge - canary

"""

def runTest(test, options, global_options, reactor=reactor):
    """
    Run an OONI probe test by name.

    @param test: a string specifying the test name as specified inside of
                 shortName.

    @param options: the local options to be passed to the test.

    @param global_options: the global options for OONI
    """
    parallelism = int(global_options['parallelism'])
    worker = work.Worker(parallelism, reactor=reactor)
    test_class = plugoo[test].__class__
    report = reports.Report(test, global_options['output'])

    log_to_stdout = True
    if global_options['quiet']:
        log_to_stdout = False

    log.start(log_to_stdout,
              global_options['log'],
              global_options['verbosity'])

    resume = 0
    if not options:
        options = {}
    if 'resume' in options:
        resume = options['resume']

    test = test_class(options, global_options, report, reactor=reactor)
    if test.tool:
        test.runTool()
        return True

    if test.ended:
        print "Ending test"
        return None

    wgen = work.WorkGenerator(test,
                              dict(options),
                              start=resume)
    for x in wgen:
        worker.push(x)

class MainOptions(usage.Options):
    tests = [bridget, ]
    subCommands = []
    for test in tests:
        print test
        testopt = getattr(test, 'options')
        subCommands.append([test, None, testopt, "Run the %s test" % test])

    optFlags = [
        ['quiet', 'q', "Don't log to stdout"]
    ]

    optParameters = [
        ['parallelism', 'n', 10, "Specify the number of parallel tests to run"],
        #['target-node', 't', 'localhost:31415', 'Select target node'],
        ['output', 'o', 'bridge.log', "Specify output report file"],
        ['reportfile', 'o', 'bridge.log', "Specify output log file"],
        ['verbosity', 'v', 1, "Specify the logging level"],
    ]

    def opt_version(self):
        """
        Display OONI version and exit.
        """
        print "OONI version:", __version__
        sys.exit(0)

    def __str__(self):
        """
        Hack to get the sweet ascii art into the help output and replace the
        strings "Commands" with "Tests".
        """
        return getlogo() + '\n' + self.getSynopsis() + '\n' + \
               self.getUsage(width=None).replace("Commands:", "Tests:")



def isTestCase(thing):
    try:
        return issubclass(thing, unittest.TestCase)
    except TypeError:
        return False

def isLegacyTest(obj):
    """
    Returns True if the test in question is written using the OONITest legacy
    class.
    We do this for backward compatibility of the OONIProbe API.
    """
    try:
        if issubclass(obj, oonitests.OONITest) and not obj == oonitests.OONITest:
                return True
        else:
            return False
    except TypeError:
        return False

def processTest(obj, config):
    """
    Process the parameters and :class:`twisted.python.usage.Options` of a
    :class:`ooni.nettest.Nettest`.

    :param obj:
        An uninstantiated old test, which should be a subclass of
        :class:`ooni.plugoo.tests.OONITest`.
    :param config:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    """

    inputFile = obj.inputFile

    if obj.optParameters or inputFile:
        if not obj.optParameters:
            obj.optParameters = []

        if inputFile:
            obj.optParameters.append(inputFile)

        class Options(usage.Options):
            optParameters = obj.optParameters

        options = Options()
        options.parseOptions(config['subArgs'])
        obj.localOptions = options

        if inputFile:
            obj.inputFile = options[inputFile[0]]
        try:
            tmp_obj = obj()
            tmp_obj.getOptions()
        except usage.UsageError:
            options.opt_help()

    return obj

def findTestClassesFromConfig(config):
    """
    Takes as input the command line config parameters and returns the test
    case classes.
    If it detects that a certain test class is using the old OONIProbe format,
    then it will adapt it to the new testing system.

    :param config:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    :return:
        A list of class objects found in a file or module given on the
        commandline.
    """

    filename = config['test']
    classes = []

    module = filenameToModule(filename)
    for name, val in inspect.getmembers(module):
        if isTestCase(val):
            classes.append(processTest(val, config))
        elif isLegacyTest(val):
            classes.append(adapt_legacy_test(val, config))
    return classes

def makeTestCases(klass, tests, methodPrefix):
    """
    Takes a class some tests and returns the test cases. methodPrefix is how
    the test case functions should be prefixed with.
    """

    cases = []
    for test in tests:
        cases.append(klass(methodPrefix+test))
    return cases

def loadTestsAndOptions(classes, config):
    """
    Takes a list of classes and returns their testcases and options.
    Legacy tests will be adapted.
    """

    methodPrefix = 'test'
    suiteFactory = InputTestSuite
    options = []
    testCases = []
    names = []

    _old_klass_type = LegacyOONITest

    for klass in classes:
        if isinstance(klass, _old_klass_type):
            try:
                cases = start_legacy_test(klass)
                #cases.callback()
                if cases:
                    print cases
                    return [], []
                testCases.append(cases)
            except Exception, e:
                log.err(e)
            else:
                try:
                    opts = klass.local_options
                    options.append(opts)
                except AttributeError, ae:
                    options.append([])
                    log.err(ae)
        elif not isinstance(klass, _old_klass_type):
            tests = reflect.prefixedMethodNames(klass, methodPrefix)
            if tests:
                cases = makeTestCases(klass, tests, methodPrefix)
                testCases.append(cases)
            try:
                k = klass()
                opts = k.getOptions()
                options.append(opts)
            except AttributeError, ae:
                options.append([])
                log.err(ae)
        else:
            try:
                raise RuntimeError, "Class is some strange type!"
            except RuntimeError, re:
                log.err(re)

    return testCases, options

class ORunner(object):
    """
    This is a specialized runner used by the ooniprobe command line tool.
    I am responsible for reading the inputs from the test files and splitting
    them in input units. I also create all the report instances required to run
    the tests.
    """
    def __init__(self, cases, options=None, config=None, *arg, **kw):
        self.baseSuite = InputTestSuite
        self.cases = cases
        self.options = options

        try:
            assert len(options) != 0, "Length of options is zero!"
        except AssertionError, ae:
            self.inputs = []
            log.err(ae)
        else:
            try:
                first = options.pop(0)
            except:
                first = {}
            if 'inputs' in first:
                self.inputs = options['inputs']
            else:
                log.msg("Could not find inputs!")
                log.msg("options[0] = %s" % first)
                self.inputs = [None]

        try:
            reportFile = open(config['reportfile'], 'a+')
        except:
            filename = 'report_'+date.timestamp()+'.yaml'
            reportFile = open(filename, 'a+')
        self.reporterFactory = ReporterFactory(reportFile,
                                               testSuite=self.baseSuite(self.cases))

    def runWithInputUnit(self, inputUnit):
        idx = 0
        result = self.reporterFactory.create()

        for inputs in inputUnit:
            result.reporterFactory = self.reporterFactory

            suite = self.baseSuite(self.cases)
            suite.input = inputs
            suite(result, idx)

            # XXX refactor all of this index bullshit to avoid having to pass
            # this index around. Probably what I want to do is go and make
            # changes to report to support the concept of having multiple runs
            # of the same test.
            # We currently need to do this addition in order to get the number
            # of times the test cases that have run inside of the test suite.
            idx += (suite._idx - idx)

        result.done()

    def run(self):
        self.reporterFactory.options = self.options
        for inputUnit in InputUnitFactory(self.inputs):
            self.runWithInputUnit(inputUnit)

if __name__ == "__main__":
    config = Options()
    config.parseOptions()

    if not config.subCommand:
        config.opt_help()
        signal(SIGTERM)
        #sys.exit(1)

    runTest(config.subCommand, config.subOptions, config)
    reactor.run()

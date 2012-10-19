import os
import sys
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

        try:
            assert not isinstance(klass, _old_klass_type), "Legacy test detected"
        except:
            assert isinstance(klass, _old_klass_type)
            try:
                start_legacy_test(klass)
            except Exception, e:
                log.err(e)
        else:
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


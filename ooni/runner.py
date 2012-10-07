import os
import sys
import types
import time
import inspect

from twisted.internet import defer, reactor
from twisted.python import reflect, failure, usage

from twisted.python import log as tlog

from twisted.trial import unittest
from twisted.trial.runner import TrialRunner, TestLoader
from twisted.trial.runner import isPackage, isTestCase, ErrorHolder
from twisted.trial.runner import filenameToModule, _importFromFile

from ooni.reporter import ReporterFactory
from ooni.inputunit import InputUnitFactory
from ooni.nettest import InputTestSuite
from ooni import nettest
from ooni.utils import log, geodata, date
from ooni.plugoo import tests as oonitests

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

def adaptLegacyTest(obj, config):
    """
    We take a legacy OONITest class and convert it into a nettest.TestCase.
    This allows backward compatibility of old OONI tests.

    XXX perhaps we could implement another extra layer that makes the even
    older test cases compatible with the new OONI.
    """
    class legacy_reporter(object):
        def __init__(self, report_target):
            self.report_target = report_target

        def __call__(self, what):
            self.report_target.append(what)

    class LegacyOONITest(nettest.TestCase):
        try:
            name = obj.shortName
        except:
            name = "LegacyOONITest"

        originalTest = obj

        subOptions = obj.options()
        subOptions.parseOptions(config['subArgs'])

        test_class = obj(None, None, None, None)
        test_class.local_options = subOptions
        assets = test_class.load_assets()

        inputs = [None]
        # XXX here we are only taking assets that are set to one item only.
        for key, inputs in assets.items():
            pass

        inputs = inputs
        local_options = subOptions

        @defer.inlineCallbacks
        def test_start_legacy_test(self):

            self.legacy_report = []

            my_test = self.originalTest(None, None, None)
            my_test.report = legacy_reporter(self.legacy_report)
            args = {}
            args[self.key] = self.input
            result = yield my_test.startTest(args)
            self.report['result'] = result

    return LegacyOONITest

def processTest(obj, config):
    if obj.optParameters or obj.inputFile:
        if not obj.optParameters:
            obj.optParameters = []

        class Options(usage.Options):
            optParameters = obj.optParameters

        inputFile = obj.inputFile
        if inputFile:
            Options.optParameters.append(inputFile)

        print Options.optParameters
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
    """
    filename = config['test']

    classes = []

    module = filenameToModule(filename)
    for name, val in inspect.getmembers(module):
        if isTestCase(val):
            classes.append(processTest(val, config))
        elif isLegacyTest(val):
            classes.append(adaptLegacyTest(val, config))
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

def loadTestsAndOptions(classes):
    """
    Takes a list of classes and returnes their testcases and options.
    Legacy tests will be adapted.
    """
    methodPrefix = 'test'
    suiteFactory = InputTestSuite
    options = []
    testCases = []
    names = []

    for klass in classes:
        try:
            k = klass()
            opts = k.getOptions()
            options.append(opts)
        except AttributeError:
            options.append([])
        tests = reflect.prefixedMethodNames(klass, methodPrefix)
        if tests:
            cases = makeTestCases(klass, tests, methodPrefix)
            testCases.append(cases)
        else:
            options.pop()

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
        self.inputs = options['inputs']
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

        for input in inputUnit:
            result.reporterFactory = self.reporterFactory

            suite = self.baseSuite(self.cases)
            suite.input = input
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
        log.start()

        self.reporterFactory.options = self.options

        for inputUnit in InputUnitFactory(self.inputs):
            self.runWithInputUnit(inputUnit)


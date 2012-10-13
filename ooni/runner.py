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

class legacy_reporter(object):
    def __init__(self, report_target):
        self.report_target = report_target

    def __call__(self, what):
        self.report_target.append(what)

class LegacyOONITest(nettest.TestCase):

    ## we need bases so that inherited methods get parsed for prefixes too
    from ooni.plugoo.tests import OONITest
    __bases__ = (OONITest, )

    def __init__(self, obj, config):
        super(LegacyOONITest, self).__init__()
        self.originalTest = obj
        log.debug("obj: %s" % obj)
        log.debug("originalTest: %s" % self.originalTest)

        self.subArgs = (None, )
        if 'subArgs' in config:
            self.subArgs = config['subArgs']

        try:
            self.name = self.originalTest.shortName
        except:
            self.was_named = False
            self.name = "LegacyOONITest"

        try:
            self.subOptions = self.originalTest.options()
        except AttributeError:
            if self.was_named is False:
                origClass    = self.originalTest.__class__
                origClassStr = str(origClass)
                fromModule   = origClassStr.rsplit('.', 2)[:-1]
                #origNamespace = globals()[origClass]()
                #origAttr      = getattr(origNamespace, fromModule)
                log.debug("original class: %s" % origClassStr)
                log.debug("from module: %s" % fromModule)
                #log.debug("orginal namespace: %s" % origNamespace)
                #log.debug("orginal attr: %s" % origAttr)

                def _options_from_name_tag(method_name,
                                           orig_test=self.originalTest):
                    return orig_test.method_name.options()

                self.subOptions = _options_from_name_tag(fromModule,
                                                         self.originalTest)
            else:
                self.subOptions = None
                log.err("That test appears to have a name, but no options!")

        if self.subOptions is not None:
            self.subOptions.parseOptions(self.subArgs)
            self.local_options = self.subOptions

        self.legacy_test = self.originalTest(None, None, None, None)
        ## xxx fix me
        #my_test.global_options = config['Options']
        self.legacy_test.local_options = self.subOptions
        if self.was_named:
            self.legacy_test.name = self.name
        else:
            self.legacy_test.name = fromModule
        self.legacy_test.assets = self.legacy_test.load_assets()
        self.legacy_test.report = legacy_reporter({})
        self.legacy_test.initialize()

        inputs = []

        if len(self.legacy_test.assets.items()) == 0:
            inputs.append('internal_asset_handler')
        else:
            for key, inputs in self.legacy_test.assets.items():
                pass
        self.inputs = inputs

    def __getattr__(self, name):
        def method(*args):
            log.msg("Call to unknown method %s.%s" % (self.originalTest, name))
            if args:
                log.msg("Unknown method %s parameters: %s" % str(args))
        return method

    @defer.inlineCallbacks
    def test_start_legacy_test(self):
        args = {}
        for key, inputs in self.legacy_test.assets.items():
            args[key] = inputs
            result = yield self.legacy_test.startTest(args)
            self.report.update({'result':  result})
        ## xxx we need to retVal on the defer.inlineCallbacks, right?
        defer.returnValue(self.report)

def adaptLegacyTest(obj, config):
    """
    We take a legacy OONITest class and convert it into a nettest.TestCase.
    This allows backward compatibility of old OONI tests.

    XXX perhaps we could implement another extra layer that makes the even
    older test cases compatible with the new OONI.
    """
    return LegacyOONITest(obj, config)

def processTest(obj, config):
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

def loadTestsAndOptions(classes, config):
    """
    Takes a list of classes and returnes their testcases and options.
    Legacy tests will be adapted.
    """
    methodPrefix = 'test'
    suiteFactory = InputTestSuite
    options = []
    testCases = []
    names = []

    from ooni.runner import LegacyOONITest
    _old_klass_type = LegacyOONITest

    for klass in classes:

        try:
            assert not isinstance(klass, _old_klass_type)
        except:
            assert isinstance(klass, _old_klass_type)
            #log.debug(type(klass))
            #legacyTest = adaptLegacyTest(klass, config)
            klass.test_start_legacy_test()
        else:
            tests = reflect.prefixedMethodNames(klass, methodPrefix)
            if tests:
                cases = makeTestCases(klass, tests, methodPrefix)
                testCases.append(cases)
            try:
                k = klass()
                opts = k.getOptions()
                options.append(opts)
            except AttributeError:
                options.append([])

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
        self.reporterFactory.options = self.options
        for inputUnit in InputUnitFactory(self.inputs):
            self.runWithInputUnit(inputUnit)


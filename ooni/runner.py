#-*- coding: utf-8 -*-
#
# runner.py
# ---------
# Handles running ooni.nettests as well as ooni.plugoo.tests.OONITests.
#
# :authors: Isis Lovecruft, Arturo Filasto
# :license: see included LICENSE file
# :copyright: (c) 2012 Isis Lovecruft, Arturo Filasto, The Tor Project, Inc.
# :version: 0.1.0-pre-alpha
#
import os
import inspect

from twisted.python import reflect, usage

from twisted.trial.runner import isTestCase
from twisted.trial.runner import filenameToModule

from ooni.inputunit import InputUnitFactory
from ooni.nettest import InputTestSuite, NetTestCase
from ooni.plugoo import tests as oonitests
from ooni.reporter import ReporterFactory
from ooni.utils import log, date
from ooni.utils.legacy import LegacyOONITest
from ooni.utils.legacy import start_legacy_test, adapt_legacy_test


def isTemplate(obj):
    origin = obj.__module__
    if origin.find('templates') >= 0:
        return True
    return False

def isLegacyTest(obj):
    """
    Returns True if the test in question is written using the OONITest legacy
    class.
    We do this for backward compatibility of the OONIProbe API.
    """
    try:
        return issubclass(obj, oonitests.OONITest) and not obj == oonitests.OONITest
    except TypeError:
        return False

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
            if val != NetTestCase and not isTemplate(val):
                log.debug("findTestClassesFromConfig: detected %s"
                          % val.__name__)
                classes.append(val)
        elif isLegacyTest(val):
            log.debug("Detected Legacy Test %s" % val)
            classes.append(adapt_legacy_test(val, config))
    return classes

def makeTestCases(klass, tests, method_prefix=None):
    """
    Takes a class some tests and returns the test cases. method_prefix is how
    the test case functions should be prefixed with.
    """
    if not method_prefix:
        method_prefix = 'test'

    cases = []
    for test in tests:
        log.debug("makeTestCases: making test case for %s" % test)
        method_name = str(method_prefix)+str(test)
        log.debug("makeTestCases: using methodName=%s" % method_name)
        cases.append(klass(methodName=method_name))
    return cases

def getTestOptions(cls, subargs):
    """
    Process the parameters and :class:`twisted.python.usage.Options` of a
    :class:`ooni.nettest.Nettest`.

    :param cls:
        An subclass of :class:`ooni.nettest.NetTestCase`.
    :param config:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    """
    if cls.requiresRoot:
        if os.getuid() != 0:
            raise Exception("This test requires root to run")

    try:
        local_opts = cls.buildOptions(subargs)
    except Exception, e:
        log.err(e)

    log.debug("getTestOptions: local_options = %s" % local_opts)

    return local_opts

def loadTestsAndOptions(classes, config):
    """
    Takes a list of test classes and returns their testcases and options.
    Legacy tests will be adapted.
    """
    from inspect import isclass

    method_prefix = 'test'
    options = []
    test_cases = []

    DEPRECATED = LegacyOONITest

    for klass in classes:
        if isinstance(klass, DEPRECATED):
            try:
                cases, opts = processLegacyTest(klass, config)
                if cases:
                    log.debug("loadTestsAndOptions: processing cases %s"
                              % str(cases))
                    return [], []
                test_cases.append(cases)
            except Exception, e: log.err(e)
            else:
                try:
                    opts = klass.local_options
                    option.append(opts)
                except AttributeError, ae:
                    options.append([])
                    log.err(ae)

        elif issubclass(klass, NetTestCase):
            try:
                cases, opts = processNetTest(klass, config, method_prefix)
            except Exception, e:
                log.err(e)
            else:
                test_cases.append(cases)
                options.append(opts)

    return test_cases, options

def processNetTest(klass, config, method_prefix):
    try:
        klass.setUpClass()
    except Exception, e:
        log.err(e)

    subargs_from_config = config['subArgs']
    log.debug("processNetTest: received subargs from config: %s"
              % str(subargs_from_config))
    try:
        opts = getTestOptions(klass, subargs_from_config)
    except Exception, e:
        opts = []
        log.err(e)

    try:
        log.debug("processNetTest: processing cases for %s"
                  % (klass.name if hasattr(klass, 'name') else 'Network Test'))
        tests = reflect.prefixedMethodNames(klass, method_prefix)
    except Exception, e:
        cases = []
        opts = []
        log.err(e)
    else:
        if tests:
            cases = makeTestCases(klass, tests, method_prefix)
            log.debug("processNetTest: test %s found cases %s"
                      % (tests, cases))
        else:
            cases = []

    return cases, opts

def processLegacyTest(klass, config):
    log.msg("Processing cases and options for legacy test %s"
            % ( klass.shortName if hasattr(klass, shortName) else 'oonitest' ))
    if hasattr(klass, description):
        log.msg("%s" % klass.description)

    subcmds = []
    if hasattr(klass, options):        ## an unitiated Legacy test
        log.debug("%s.options found: %s " % (klass, klass.options))
        try:
            assert isclass(klass.options), "legacytest.options is not class"
        except AssertionError, ae:
            log.debug(ae)
        else:
            ok = klass.options
            ok.parseArgs = lambda x: subcmds.append(x)
            try:
                opts = ok()
                opts.parseOptions(config['subArgs'])
            except Exception, e:
                log.err(e)
                opts = {}

    elif hasattr(klass, local_options): ## we've been initialized already
        log.debug("processLegacyTest: %s.local_options found" % str(klass))
        try:
            opts = klass.local_options
        except AttributeError, ae: opts = {}; log.err(ae)
        log.debug("processLegacyTest: opts set to %s" % str(opts))

    try:
        cases = start_legacy_test(klass)
        ## XXX we need to get these results into the reporter
        if cases:
            log.debug("processLegacyTest: found cases: %s" % str(cases))
            return [], []
    except Exception, e: cases = []; log.err(e)

    return cases, opts

class ORunner(object):
    """
    This is a specialized runner used by the ooniprobe command line tool.
    I am responsible for reading the inputs from the test files and splitting
    them in input units. I also create all the report instances required to run
    the tests.
    """
    def __init__(self, cases, options=None, config=None):
        self.baseSuite = InputTestSuite
        self.cases = cases
        self.options = options

        log.debug("ORunner: cases=%s" % type(cases))
        log.debug("ORunner: options=%s" % options)

        try:
            first = options.pop(0)
        except:
            first = options

        if 'inputs' in first:
            self.inputs = self.options['inputs']
        else:
            log.msg("Could not find inputs!")
            self.inputs = [None]

        try:
            reportFile = open(config['reportfile'], 'a+')
        except:
            filename = 'report_'+date.timestamp()+'.yaml'
            reportFile = open(filename, 'a+')
        self.reporterFactory = ReporterFactory(
            reportFile, testSuite=self.baseSuite(self.cases))

    def runWithInputUnit(self, input_unit):
        idx = 0
        result = self.reporterFactory.create()
        log.debug("Running test with input unit %s" % input_unit)
        for inputs in input_unit:
            result.reporterFactory = self.reporterFactory

            log.debug("Running with %s" % inputs)
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
            log.debug("I am now at the index %s" % idx)

        log.debug("Finished")
        result.done()

    def run(self):
        self.reporterFactory.options = self.options
        for input_unit in InputUnitFactory(self.inputs):
            self.runWithInputUnit(input_unit)

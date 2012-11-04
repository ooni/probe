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

    input_file = obj.inputFile
    if obj.requiresRoot:
        if os.getuid() != 0:
            raise Exception("This test requires root to run")

    if obj.optParameters or input_file:
        if not obj.optParameters:
            obj.optParameters = []

        if input_file:
            obj.optParameters.append(input_file)

        class Options(usage.Options):
            optParameters = obj.optParameters

        options = Options()
        options.parseOptions(config['subArgs'])
        obj.localOptions = options

        if input_file:
            obj.inputFile = options[input_file[0]]
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
            log.debug("Detected TestCase %s" % val)
            classes.append(val)
        elif isLegacyTest(val):
            log.debug("Detected Legacy Test %s" % val)
            classes.append(adapt_legacy_test(val, config))
    return classes

def makeTestCases(klass, tests, method_prefix):
    """
    Takes a class some tests and returns the test cases. method_prefix is how
    the test case functions should be prefixed with.
    """
    cases = []
    for test in tests:
        cases.append(klass(method_prefix+test))
    return cases

def processTestOptions(cls, config):
    """
    Process the parameters and :class:`twisted.python.usage.Options` of a
    :class:`ooni.nettest.Nettest`.

    :param cls:
        An subclass of :class:`ooni.nettest.NetTestCase`.
    :param config:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    """
    #if cls.optParameters or cls.inputFile:
    if not cls.optParameters:
        cls.optParameters = []

    if cls.inputFile:
        cls.optParameters.append(cls.inputFile)

    log.debug("CLS IS %s" % cls)
    log.debug("CLS OPTPARAM IS %s" % cls.optParameters)

    #if not hasattr(cls, subCommands):
    #    cls.subCommands = []

    if not cls.subCommands:
        cls.subCommands = []

    class Options(usage.Options):
        optParameters = cls.optParameters
        parseArgs     = lambda a: cls.subCommands.append(a)

    opts = Options()
    opts.parseOptions(config['subArgs'])
    cls.localOptions = opts

    if cls.inputFile:
        cls.inputFile = opts[cls.inputFile[0]]
    """
    try:
        log.debug("%s: trying %s.localoptions.getOptions()..."
                  % (__name__, cls.name))
        try:
            assert hasattr(cls, 'getOptions')
        except AssertionError, ae:
            options = opts.opt_help()
            raise Exception, "Cannot find %s.getOptions()" % cls.name
        else:
            options = cls.getOptions()
    except usage.UsageError:
        options = opts.opt_help()
    else:
    """
    return cls.localOptions

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
            #not issubclass(klass, TestCase):
            try:
                cases, opts = processLegacyTest(klass, config)
                if cases:
                    log.debug("Processing cases: %s" % str(cases))
                    return [], []
                test_cases.append(cases)
            except Exception, e:
                log.err(e)
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
        log.debug("Processing cases and options for OONI %s test"
                  % (klass.name if hasattr(klass, 'name') else 'Network Test'))

        tests = reflect.prefixedMethodNames(klass, method_prefix)
        if tests:
            cases = makeTestCases(klass, tests, method_prefix)
            log.debug("loadTestsAndOptions(): test %s found cases=%s"% (tests, cases))
            try:
                k = klass()
                opts = processTestOptions(k, config)
            except Exception, e:
                opts = []
                log.err(e)
        else:
            cases = []
    except Exception, e:
        log.err(e)

    return cases, opts

'''
    if hasattr(klass, 'optParameters') or hasattr(klass, 'inputFile'):
        try:
            opts = processTestOptions(klass, config)
        except:
            opts = []
        finally:
            try:
                k = klass()
                inputs = k._getInputs()
            except Exception, e:
                inputs = []
                log.err(e)
            else:
                if opts and len(inputs) != 0:
                    opts.append(['inputs', '', inputs, "cmdline inputs"])
        log.debug("loadTestsAndOptions(): inputs=%s" % inputs)
'''

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
        log.debug("%s.local_options found" % klass)
        try:
            assert klass.local_options is not None
            opts = klass.local_options
        except AttributeError, ae:
            opts = {}; log.err(ae)

    try:
        cases = start_legacy_test(klass)
        ## XXX we need to get these results into the reporter
        if cases:
            return [], []
    except Exception, e:
        cases = []; log.err(e)
    finally:
        log.debug(str(cases))

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

        try:
            assert len(options) != 0, "Length of options is zero!"
        except AssertionError, ae:
            log.err(ae)
            self.inputs = []
        else:
            try:
                first = options.pop(0)
            except:
                first = options

            if 'inputs' in first:
                self.inputs = options['inputs']
            else:
                log.msg("Could not find inputs!")
                self.inputs = [None]

        try:
            reportFile = open(config['reportfile'], 'a+')
        except:
            filename = 'report_'+date.timestamp()+'.yaml'
            reportFile = open(filename, 'a+')
        self.reporterFactory = ReporterFactory(
            reportFile, testSuite=self.baseSuite(self.cases)
            )

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

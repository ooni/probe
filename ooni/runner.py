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

import inspect

from twisted.python import reflect, usage

from twisted.trial.runner import isTestCase
from twisted.trial.runner import filenameToModule

from ooni.inputunit import InputUnitFactory
from ooni.nettest import InputTestSuite
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
            classes.append(processTest(val, config))
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

def loadTestsAndOptions(classes, config):
    """
    Takes a list of test classes and returns their testcases and options.
    Legacy tests will be adapted.
    """

    method_prefix = 'test'
    options = []
    test_cases = []

    _old_klass_type = LegacyOONITest

    for klass in classes:
        if isinstance(klass, _old_klass_type):
            try:
                cases = start_legacy_test(klass)
                if cases:
                    log.debug("Processing cases")
                    log.debug(str(cases))
                    return [], []
                test_cases.append(cases)
            except Exception, e:
                log.err(e)
            else:
                try:
                    opts = klass.local_options
                    options.append(opts)
                except AttributeError, ae:
                    options.append([])
                    log.err(ae)
        else:
            tests = reflect.prefixedMethodNames(klass, method_prefix)
            if tests:
                cases = makeTestCases(klass, tests, method_prefix)
                test_cases.append(cases)
            try:
                k = klass()
                opts = k.getOptions()
                options.append(opts)
            except AttributeError, ae:
                options.append([])
                log.err(ae)

    return test_cases, options

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
            self.inputs = []
            log.err(ae)
        else:
            try:
                first = options.pop(0)
            except:
                first = options

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

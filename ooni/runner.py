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

import os
import inspect

from twisted.python import reflect, usage

from twisted.trial.runner import isTestCase
from twisted.trial.runner import filenameToModule

from ooni.inputunit import InputUnitFactory
from ooni.nettest import InputTestSuite

from ooni.reporter import ReporterFactory
from ooni.utils import log, date
from ooni import config

def processTest(obj, cmd_line_options):
    """
    Process the parameters and :class:`twisted.python.usage.Options` of a
    :class:`ooni.nettest.Nettest`.

    :param obj:
        An uninstantiated old test, which should be a subclass of
        :class:`ooni.plugoo.tests.OONITest`.
    :param cmd_line_options:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    """

    input_file = obj.inputFile
    if obj.requiresRoot:
        if os.getuid() != 0:
            raise Exception("This test requires root to run")

    if obj.optParameters or input_file \
            or obj.usageOptions or obj.optFlags:

        if not obj.optParameters:
            obj.optParameters = []

        if input_file:
            obj.optParameters.append(input_file)

        if obj.usageOptions:
            if input_file:
                obj.usageOptions.optParameters.append(input_file)
            options = obj.usageOptions()
        else:
            # XXX this as suggested by isis should be removed.
            log.debug("Got optParameters")
            class Options(usage.Options):
                optParameters = obj.optParameters
                if obj.optFlags:
                    log.debug("Got optFlags")
                    optFlags = obj.optFlags

            options = Options()

        options.parseOptions(cmd_line_options['subArgs'])
        obj.localOptions = options

        if input_file:
            obj.inputFile = options[input_file[0]]

        try:
            tmp_test_case_object = obj()
            tmp_test_case_object._processOptions(options)

        except usage.UsageError, e:
            print "There was an error in running %s!" % tmp_test_case_object.name
            print "%s" % e
            options.opt_help()

    return obj

def findTestClassesFromConfig(cmd_line_options):
    """
    Takes as input the command line config parameters and returns the test
    case classes.
    If it detects that a certain test class is using the old OONIProbe format,
    then it will adapt it to the new testing system.

    :param cmd_line_options:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    :return:
        A list of class objects found in a file or module given on the
        commandline.
    """

    filename = cmd_line_options['test']
    classes = []

    module = filenameToModule(filename)
    for name, val in inspect.getmembers(module):
        if isTestCase(val):
            log.debug("Detected TestCase %s" % val)
            classes.append(processTest(val, cmd_line_options))
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

def loadTestsAndOptions(classes, cmd_line_options):
    """
    Takes a list of test classes and returns their testcases and options.
    """
    method_prefix = 'test'
    options = []
    test_cases = []

    for klass in classes:
        tests = reflect.prefixedMethodNames(klass, method_prefix)
        if tests:
            cases = makeTestCases(klass, tests, method_prefix)
            test_cases.append(cases)
        try:
            k = klass()
            opts = k._processOptions()
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
    def __init__(self, cases, options=None, cmd_line_options=None):
        self.baseSuite = InputTestSuite
        self.cases = cases
        self.options = options

        log.debug("ORunner: cases=%s" % type(cases))
        log.debug("ORunner: options=%s" % options)

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

        if cmd_line_options['reportfile']:
            report_filename = cmd_line_options['reportfile']
        else:
            report_filename = 'report_'+date.timestamp()+'.yamloo'

        if os.path.exists(report_filename):
            print "Report already exists with filename %s" % report_filename
            print "Renaming it to %s" % report_filename+'.old'
            os.rename(report_filename, report_filename+'.old')

        reportFile = open(report_filename, 'w+')
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

        config.threadpool.stop()

    def run(self):
        self.reporterFactory.options = self.options
        for input_unit in InputUnitFactory(self.inputs):
            self.runWithInputUnit(input_unit)

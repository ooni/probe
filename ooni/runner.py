#-*- coding: utf-8 -*-
#
# runner.py
# ---------
# Handles running ooni.nettests as well as
# ooni.plugoo.tests.OONITests.
#
# :authors: Arturo Filastò, Isis Lovecruft
# :license: see included LICENSE file

import os
import sys
import time
import inspect
import traceback
import itertools

from twisted.python import reflect, usage
from twisted.internet import defer
from twisted.trial.runner import filenameToModule
from twisted.internet import reactor, threads

from ooni.inputunit import InputUnitFactory
from ooni.nettest import NetTestCase, NoPostProcessor

from ooni import reporter, config

from ooni.utils import log, checkForRoot, NotRootError

def processTest(obj):
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
    if not hasattr(obj.usageOptions, 'optParameters'):
        obj.usageOptions.optParameters = []

    if obj.inputFile:
        obj.usageOptions.optParameters.append(obj.inputFile)

    if obj.baseParameters:
        for parameter in obj.baseParameters:
            obj.usageOptions.optParameters.append(parameter)

    if obj.baseFlags:
        if not hasattr(obj.usageOptions, 'optFlags'):
            obj.usageOptions.optFlags = []
        for flag in obj.baseFlags:
            obj.usageOptions.optFlags.append(flag)

    options = obj.usageOptions()

    options.parseOptions(config.cmd_line_options['subargs'])
    obj.localOptions = options

    if obj.inputFile:
        obj.inputFilename = options[obj.inputFile[0]]

    try:
        log.debug("processing options")
        tmp_test_case_object = obj()
        tmp_test_case_object._processOptions(options)

    except usage.UsageError, e:
        test_name = tmp_test_case_object.name
        log.err("There was an error in running %s!" % test_name)
        log.err("%s" % e)
        options.opt_help()
        raise usage.UsageError("Error in parsing command line args for %s" % test_name)

    if obj.requiresRoot:
        try:
            checkForRoot()
        except NotRootError:
            log.err("%s requires root to run" % obj.name)
            sys.exit(1)

    return obj

def isTestCase(obj):
    try:
        return issubclass(obj, NetTestCase)
    except TypeError:
        return False

def findTestClassesFromFile(filename):
    """
    Takes as input the command line config parameters and returns the test
    case classes.

    :param filename:
        the absolute path to the file containing the ooniprobe test classes

    :return:
        A list of class objects found in a file or module given on the
        commandline.
    """
    classes = []
    module = filenameToModule(filename)
    for name, val in inspect.getmembers(module):
        if isTestCase(val):
            classes.append(processTest(val))
    return classes

def makeTestCases(klass, tests, method_prefix):
    """
    Takes a class some tests and returns the test cases. method_prefix is how
    the test case functions should be prefixed with.
    """
    cases = []
    for test in tests:
        cases.append((klass, method_prefix+test))
    return cases

def loadTestsAndOptions(classes, cmd_line_options):
    """
    Takes a list of test classes and returns their testcases and options.
    """
    method_prefix = 'test'
    options = None
    test_cases = []

    for klass in classes:
        tests = reflect.prefixedMethodNames(klass, method_prefix)
        if tests:
            test_cases = makeTestCases(klass, tests, method_prefix)

        test_klass = klass()
        options = test_klass._processOptions(cmd_line_options)

    return test_cases, options

def runTestCasesWithInput(test_cases, test_input, oreporter):
    """
    Runs in parallel all the test methods that are inside of the specified test case.
    Reporting happens every time a Test Method has concluded running.
    Once all the test methods have been called we check to see if the
    postProcessing class method returns something. If it does return something
    we will write this as another entry inside of the report called post_processing.
    """

    # This is used to store a copy of all the test reports
    tests_report = {}

    def test_done(result, test_instance, test_name):
        log.debug("runTestWithInput: concluded %s" % test_name)
        tests_report[test_name] = dict(test_instance.report)
        return oreporter.testDone(test_instance, test_name)

    def test_error(failure, test_instance, test_name):
        log.exception(failure)

    def tests_done(result, test_class):
        test_instance = test_class()
        test_instance.report = {}
        test_instance.input = None
        test_instance._start_time = time.time()
        post = getattr(test_instance, 'postProcessor')
        try:
            post_processing = post(tests_report)
            return oreporter.testDone(test_instance, 'summary')
        except NoPostProcessor:
            log.debug("No post processor configured")

    dl = []
    for test_case in test_cases:
        log.debug("Processing %s" % test_case[1])
        test_class = test_case[0]
        test_method = test_case[1]

        log.msg("Running %s with %s" % (test_method, test_input))

        test_instance = test_class()
        test_instance.input = test_input
        test_instance.report = {}
        log.msg("Processing %s" % test_instance.name)
        # use this to keep track of the test runtime
        test_instance._start_time = time.time()
        # call setups on the test
        test_instance._setUp()
        test_instance.setUp()
        test = getattr(test_instance, test_method)

        d = defer.maybeDeferred(test)
        d.addCallback(test_done, test_instance, test_method)
        d.addErrback(test_error, test_instance, test_method)
        log.debug("returning %s input" % test_method)
        dl.append(d)

    test_methods_d = defer.DeferredList(dl)
    test_methods_d.addCallback(tests_done, test_cases[0][0])
    return test_methods_d

def runTestCasesWithInputUnit(test_cases, input_unit, oreporter):
    """
    Runs the Test Cases that are given as input parallely.
    A Test Case is a subclass of ooni.nettest.NetTestCase and a list of
    methods.

    The deferred list will fire once all the test methods have been
    run once per item in the input unit.

    test_cases: A list of tuples containing the test class and the test method as a string.

    input_unit: A generator that yields an input per iteration

    oreporter: An instance of a subclass of ooni.reporter.OReporter
    """
    log.debug("Running test cases with input unit")
    dl = []
    for test_input in input_unit:
        log.debug("Running test with this input %s" % test_input)
        d = runTestCasesWithInput(test_cases, test_input, oreporter)
        dl.append(d)
    return defer.DeferredList(dl)

@defer.inlineCallbacks
def runTestCases(test_cases, options, cmd_line_options):
    log.debug("Running %s" % test_cases)
    log.debug("Options %s" % options)
    log.debug("cmd_line_options %s" % dict(cmd_line_options))
    try:
        assert len(options) != 0, "Length of options is zero!"
    except AssertionError, ae:
        test_inputs = []
        log.err(ae)
    else:
        try:
            first = options.pop(0)
        except:
            first = options

        if 'inputs' in first:
            test_inputs = options['inputs']
        else:
            log.msg("Could not find inputs!")
            log.msg("options[0] = %s" % first)
            test_inputs = [None]

    if cmd_line_options['collector']:
        log.debug("Using remote collector")
        oreporter = reporter.OONIBReporter(cmd_line_options)
    else:
        log.debug("Reporting to file %s" % config.reports.yamloo)
        oreporter = reporter.YAMLReporter(cmd_line_options)

    try:
        input_unit_factory = InputUnitFactory(test_inputs)
    except Exception, e:
        log.exception(e)

    log.debug("Creating report")

    try:
        yield oreporter.createReport(options)
    except reporter.OONIBReportCreationFailed:
        log.err("Error in creating new report")
        reactor.stop()
        raise
    except Exception, e:
        log.exception(e)

    # This deferred list is a deferred list of deferred lists
    # it is used to store all the deferreds of the tests that
    # are run
    input_unit_idx = 0
    try:
        for input_unit in input_unit_factory:
            log.debug("Running this input unit %s" % input_unit)
            yield runTestCasesWithInputUnit(test_cases, input_unit,
                        oreporter)
            input_unit_idx += 1

    except Exception:
        log.exception("Problem in running test")
        reactor.stop()
    oreporter.allDone()


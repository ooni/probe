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
from ooni.nettest import NetTestCase

from ooni import reporter

from ooni.utils import log, checkForRoot, NotRootError

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
    options = None

    if obj.usageOptions and obj.inputFile:
        obj.usageOptions.optParameters.append(obj.inputFile)

    if obj.usageOptions and obj.baseParameters:
        if not hasattr(obj.usageOptions, 'optParameters'):
            obj.usageOptions.optParameters = []
        for parameter in obj.baseParameters:
            obj.usageOptions.optParameters.append(parameter)

    if obj.usageOptions and obj.baseFlags:
        if not hasattr(obj.usageOptions, 'optFlags'):
            obj.usageOptions.optFlags = []
        for flag in obj.baseFlags:
            obj.usageOptions.optFlags.append(flag)

    if obj.usageOptions:
        options = obj.usageOptions()

    if options:
        options.parseOptions(cmd_line_options['subArgs'])
        obj.localOptions = options

        if obj.inputFile:
            obj.inputFilename = options[obj.inputFile[0]]

        try:
            log.debug("processing options")
            tmp_test_case_object = obj()
            tmp_test_case_object._processOptions(options)

        except usage.UsageError, e:
            test_name = tmp_test_case_object.name
            print "There was an error in running %s!" % test_name
            print "%s" % e
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
            classes.append(processTest(val, cmd_line_options))
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

def runTestWithInput(test_class, test_method, test_input, oreporter):
    log.debug("Running %s with %s" % (test_method, test_input))

    def test_done(result, test_instance, test_name):
        log.debug("runTestWithInput: concluded %s" % test_name)
        return oreporter.testDone(test_instance, test_name)

    def test_error(failure, test_instance, test_name):
        log.exception(failure)

    test_instance = test_class()
    test_instance.input = test_input
    test_instance.report = {}
    log.debug("Processing %s" % test_instance.name)
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
    return d

def runTestWithInputUnit(test_class,
        test_method, input_unit, oreporter):
    """
    test_class: the uninstantiated class of the test to be run

    test_method: a string representing the method name to be called

    input_unit: a generator that contains the inputs to be run on the test

    oreporter: ooni.reporter.OReporter instance

    returns a deferred list containing all the tests to be run at this time
    """

    dl = []
    log.debug("input unit %s" % input_unit)
    for test_input in input_unit:
        log.debug("running with input: %s" % test_input)
        d = runTestWithInput(test_class,
                test_method, test_input, oreporter)
        dl.append(d)
    return defer.DeferredList(dl)

@defer.inlineCallbacks
def runTestCases(test_cases, options,
        cmd_line_options, yamloo_filename):
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

    log.debug("Creating %s" % yamloo_filename)

    if cmd_line_options['collector']:
        log.debug("Using remote collector %s" % cmd_line_options['collector'])
        oreporter = reporter.OONIBReporter(cmd_line_options['collector'])
    else:
        reportFile = open(yamloo_filename, 'w+')
        log.debug("Reporting to file %s" % reportFile)
        oreporter = reporter.YAMLReporter(reportFile)

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
    try:
        for input_unit in input_unit_factory:
            log.debug("Running this input unit %s" % input_unit)
            # We do this because generators can't we rewound.
            input_list = list(input_unit)
            for test_case in test_cases:
                log.debug("Processing %s" % test_case[1])
                test_class = test_case[0]
                test_method = test_case[1]
                yield runTestWithInputUnit(test_class,
                            test_method, input_list,
                            oreporter)
    except Exception:
        log.exception("Problem in running test")
        reactor.stop()
    oreporter.allDone()


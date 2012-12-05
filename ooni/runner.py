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

from twisted.python import reflect, usage, failure
from twisted.internet import defer
from twisted.trial.runner import filenameToModule
from twisted.trial import util as txtrutil
from twisted.trial import reporter as txreporter
from twisted.trial.unittest import utils as txtrutils
from twisted.internet import reactor, threads

from ooni.inputunit import InputUnitFactory
from ooni import reporter, nettest
from ooni.utils import log, checkForRoot, PermissionsError

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
        try:
            checkForRoot()
        except PermissionsError:
            log.err("%s requires root to run" % obj.name)
            sys.exit(1)

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
        elif obj.optParameters:
            log.debug("Got optParameters")
            class Options(usage.Options):
                optParameters = obj.optParameters
                if obj.optFlags:
                    log.debug("Got optFlags")
                    optFlags = obj.optFlags
            options = Options()

        if options:
            options.parseOptions(cmd_line_options['subArgs'])
            obj.localOptions = options

        if input_file and options:
            log.debug("Got input file")
            obj.inputFile = options[input_file[0]]

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
        if nettest.isTestCase(val):
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

def abortTestRun(test_class, warn_err_fail, test_input, oreporter):
    """
    Abort the entire test, and record the error, failure, or warning for why
    it could not be completed.
    """
    log.warn("Aborting remaining tests for %s" % test_name)

def abortTestWasCalled(abort_reason, abort_what, test_class, test_instance, 
                       test_method, test_input, oreporter):
    """
    XXX
    """
    if not abort_what in ['class', 'method', 'input']:
        log.warn("__test_abort__() must specify 'class', 'method', or 'input'")
        abort_what = 'input'    

    if not isinstance(abort_reason, Exception):
        abort_reason = Exception(str(abort_reason))
    if abort_what == 'input':
        log.msg("%s test requested to abort for input: %s"
                % (test_instance.name, test_input))
        d = defer.maybeDeferred(lambda x: object)

    if hasattr(test_instance, "abort_all"):
        log.msg("%s test requested to abort all remaining inputs"
                % test_instance.name)
    #else:
    #    d = defer.Deferred()
    #    d.cancel()
    #    d = abortTestRun(test_class, reason, test_input, oreporter)
    

def runTestWithInput(test_class, test_method, test_input, oreporter):
    """
    Runs a single testcase from a NetTestCase with one input.
    """
    log.debug("Running %s with %s" % (test_method, test_input))

    def test_abort_single_input(reason, test_instance, test_name):
        pass

    def test_timeout(d):
        err = defer.TimeoutError("%s test for %s timed out after %s seconds"
                                 % (test_name, test_instance.input, 
                                    test_instance.timeout))
        fail = failure.Failure(err)
        try:
            d.errback(fail)
        except defer.AlreadyCalledError:
            # if the deferred has already been called but the *back chain is
            # still unfinished, crash the reactor and report the timeout
            reactor.crash()
            test_instance._timedOut = True    # see test_instance._wait
            # XXX result is TestResult utils? 
            test_instance._test_result.addExpectedFailure(test_instance, fail)
    test_timeout = txtrutils.suppressWarnings(
        test_timeout, txtrutil.suppress(category=DeprecationWarning))

    def test_done(result, test_instance, test_name):
        log.debug("runTestWithInput: concluded %s" % test_name)
        return oreporter.testDone(test_instance, test_name)

    def test_error(error, test_instance, test_name):
        log.exception(error)

    test_instance = test_class()
    test_instance.input = test_input
    test_instance.report = {}
    log.debug("Processing %s" % test_instance.name)
    # use this to keep track of the test runtime
    test_instance._start_time = time.time()
    test_instance.timeout = test_instance._getTimeout()
    test_instance._test_result = txreporter.TestResult()
    # call setups on the test
    test_instance._setUp()
    test_instance.setUp()
    test_ignored = txtrutil.acquireAttribute(test_instance._parents, 
                                             'skip', None)

    test = getattr(test_instance, test_method)

    # check if we've aborted
    test_skip = test_instance._getSkip()
    if test_skip is not None:
        log.debug("%s.getSkip() returned %s" % (str(test_class), 
                                                str(test_skip)) )
 
    abort_reason, abort_what = getattr(test_instance, 'abort', ('input', None))
    if abort_reason is not None:
        do_abort = abortTestWasCalled(abort_reason, abort_what, test_class,
                                      test_instance, test_method, test_input,
                                      oreporter)
        return defer.maybeDeferred(do_abort)
    else:
        d = defer.maybeDeferred(test)

        # register the timer with the reactor
        call = reactor.callLater(test_timeout, test_timed_out, d)
        d.addBoth(lambda x: call.active() and call.cancel() or x)

        # XXX check if test called test_abort...
        d.addCallbacks(test_abort, 
                       test_error, 
                       callbackArgs=(test_instance, test_method), 
                       errbackArgs=(test_instance, test_method) )
        d.addCallback(test_done, test_instance, test_method)
        d.addErrback(test_error, test_instance, test_method)
        log.debug("returning %s input" % test_method)

        ignored = d.getSkip()

        return d

def runTestWithInputUnit(test_class, test_method, input_unit, oreporter):
    """
    @param test_class:
        The uninstantiated :class:`ooni.nettest.NetTestCase` to be run.
    @param test_method:
        A string representing the method name to be called.
    @param input_unit:
        A generator that contains the inputs to be run on the test.
    @param oreporter:
        A :class:`ooni.reporter.OReporter` instance.

    @return: A DeferredList containing all the tests to be run at this time.
    """
    dl = []
    for test_input in input_unit:
        d = runTestWithInput(test_class, test_method, test_input, oreporter)
        dl.append(d)
    return defer.DeferredList(dl)

@defer.inlineCallbacks
def runTestCases(test_cases, options, 
                 cmd_line_options, yamloo_filename):
    """
    XXX we should get rid of the InputUnit class, because we go though the
    effort of creating an iterator, only to turn it back into a list, and then
    iterate through it. it's also buggy as hell, and it's excess code.
    """
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

    reportFile = open(yamloo_filename, 'w+')

    if cmd_line_options['collector']:
        oreporter = reporter.OONIBReporter(cmd_line_options['collector'])
    else:
        oreporter = reporter.YAMLReporter(reportFile)

    input_unit_factory = InputUnitFactory(test_inputs)

    log.debug("Creating report")
    yield oreporter.createReport(options)

    # This deferred list is a deferred list of deferred lists
    # it is used to store all the deferreds of the tests that 
    # are run
    try:
        for input_unit in input_unit_factory:
            log.debug("Running this input unit %s" % input_unit)
            # We do this because generators can't be rewound.
            input_list = list(input_unit)
            for test_case in test_cases:
                log.debug("Processing %s" % test_case[1])
                test_class = test_case[0]
                test_method = test_case[1]
                yield runTestWithInputUnit(test_class, test_method,
                                           input_list, oreporter)
    except Exception, ex:
        # XXX we probably want to add a log.warn() at some point
        log.warn("Problem in running test")
        log.exception(ex)

    oreporter.allDone()
    if reactor.running:
        reactor.stop()


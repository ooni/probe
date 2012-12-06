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
from twisted.trial import reporter as txreporter
from twisted.trial import util as txtrutil
from twisted.trial.unittest import utils as txtrutils
from twisted.trial.unittest import SkipTest
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
            log.debug("Added input file to options list")
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

def getTimeout(test_instance, test_method):
    """
    Returns the timeout value set on this test. Check on the instance first,
    the the class, then the module, then package. As soon as it finds
    something with a timeout attribute, returns that. Returns
    twisted.trial.util.DEFAULT_TIMEOUT_DURATION if it cannot find anything.

    See twisted.trial.unittest.TestCase docstring for more details.
    """
    try:
        testMethod = getattr(test_instance, test_method)
    except:
        log.debug("_getTimeout couldn't find self.methodName!")
        return txtrutil.DEFAULT_TIMEOUT_DURATION
    else:
        test_instance._parents = [testMethod, test_instance]
        test_instance._parents.extend(txtrutil.getPythonContainers(testMethod))
        timeout = txtrutil.acquireAttribute(test_instance._parents, 'timeout', 
                                            txtrutil.DEFAULT_TIMEOUT_DURATION)
        try:
            return float(timeout)
        except (ValueError, TypeError):
            warnings.warn("'timeout' attribute needs to be a number.",
                          category=DeprecationWarning)
            return txtrutil.DEFAULT_TIMEOUT_DURATION

def runTestWithInput(test_class, test_method, test_input, oreporter):
    """
    Runs a single testcase from a NetTestCase with one input.
    """
    log.debug("Running %s with %s" % (test_method, test_input))

    def test_timeout(d):
        timeout_error = defer.TimeoutError(
            "%s test for %s timed out after %s seconds"
            % (test_name, test_instance.input, test_instance.timeout))
        timeout_fail = failure.Failure(err)
        try:
            d.errback(timeout_fail)
        except defer.AlreadyCalledError:
            # if the deferred has already been called but the *back chain is
            # still unfinished, crash the reactor and report the timeout
            reactor.crash()
            test_instance._timedOut = True    # see test_instance._wait
            test_instance._test_result.addExpectedFailure(test_instance, fail)
    test_timeout = txtrutils.suppressWarnings(
        test_timeout, txtrutil.suppress(category=DeprecationWarning))

    def test_done(result, test_instance, test_name):
        log.debug("Concluded %s with inputs %s"
                  % (test_name, test_instance.input))
        return oreporter.testDone(test_instance, test_name)

    def test_error(error, test_instance, test_name):
        if isinstance(error, SkipTest):
            if len(error.args) > 0:
                skip_what = error.args[1]
                # XXX we'll need to handle methods and classes
            log.info("%s" % error.message)
        else:
            log.exception(error)

    test_instance = test_class()
    test_instance.input = test_input
    test_instance.report = {}
    # XXX TODO the twisted.trial.reporter.TestResult is expected by
    # test_timeout(), but we should eventually replace it with a stub class
    test_instance._test_result = txreporter.TestResult()
    # use this to keep track of the test runtime
    test_instance._start_time = time.time()
    test_instance.timeout = getTimeout(test_instance, test_method)
    # call setups on the test
    test_instance._setUp()
    test_instance.setUp()

    test_skip = txtrutil.acquireAttribute(
        test_instance._parents, 'skip', None)
    if test_skip is not None:
        # XXX we'll need to do something more than warn
        log.warn("%s marked these tests to be skipped: %s"
                  % (test_instance.name, test_skip))
    skip_list = [test_skip]

    if not test_method in skip_list:
        test = getattr(test_instance, test_method)
        d = defer.maybeDeferred(test)

        # register the timer with the reactor
        call = reactor.callLater(test_instance.timeout, test_timeout, d)
        d.addBoth(lambda x: call.active() and call.cancel() or x)
    
        d.addCallback(test_done, test_instance, test_method)
        d.addErrback(test_error, test_instance, test_method)
    else:
        d = defer.Deferred()
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


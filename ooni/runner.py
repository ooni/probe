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
import sys
import time
import inspect
import traceback

from twisted.python import reflect, usage
from twisted.internet import defer
from twisted.trial.runner import filenameToModule

from ooni.inputunit import InputUnitFactory
from ooni.nettest import NetTestCase

from ooni import reporter
from ooni.utils import log, date

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

def runTestWithInputUnit(test_class, 
        test_method, input_unit, 
        oreporter):
    """
    test_class: the uninstantiated class of the test to be run

    test_method: a string representing the method name to be called

    input_unit: a generator that contains the inputs to be run on the test

    oreporter: ooni.reporter.OReporter instance

    returns a deferred list containing all the tests to be run at this time
    """
    def test_done(result, test_instance):
        oreporter.testDone(test_instance)

    def test_error(error, test_instance):
        log.err("%s\n" % error)

    dl = []
    for i in input_unit:
        test_instance = test_class()
        test_instance.input = i
        test_instance.report = {}
        # use this to keep track of the test runtime
        test_instance._start_time = time.time()
        # call setup on the test
        test_instance.setUp()
        test = getattr(test_instance, test_method)
        d = defer.maybeDeferred(test)
        d.addCallback(test_done, test_instance)
        d.addErrback(test_error, test_instance)
        dl.append(d)

    return defer.DeferredList(dl)

@defer.inlineCallbacks
def runTestCases(test_cases, options, cmd_line_options):
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

    if cmd_line_options['reportfile']:
        report_filename = cmd_line_options['reportfile']
    else:
        report_filename = 'report_'+date.timestamp()+'.yamloo'

    if os.path.exists(report_filename):
        print "Report already exists with filename %s" % report_filename
        print "Renaming it to %s" % report_filename+'.old'
        os.rename(report_filename, report_filename+'.old')

    reportFile = open(report_filename, 'w+')
    oreporter = reporter.OReporter(reportFile)
    input_unit_factory = InputUnitFactory(test_inputs)

    yield oreporter.writeReportHeader(options)
    # This deferred list is a deferred list of deferred lists
    # it is used to store all the deferreds of the tests that 
    # are run
    for input_unit in input_unit_factory:
        for test_case in test_cases:
            test_class = test_case[0]
            test_method = test_case[1]
            yield runTestWithInputUnit(test_class,
                        test_method, input_unit, oreporter)
    oreporter.allDone()


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
import sys
import types
import time
import inspect
import yaml

from pprint import pprint

from twisted.internet import defer, reactor
from twisted.python   import reflect, failure, usage
from twisted.python   import log as tlog

from twisted.trial        import unittest
from twisted.trial.runner import TrialRunner, TestLoader
from twisted.trial.runner import isPackage, isTestCase, ErrorHolder
from twisted.trial.runner import filenameToModule, _importFromFile

from ooni              import nettest
from ooni.inputunit    import InputUnitFactory
from ooni.nettest      import InputTestSuite
from ooni.plugoo       import tests as oonitests
from ooni.reporter     import ReporterFactory
from ooni.utils        import log, geodata, date
from ooni.utils.legacy import LegacyOONITest
from ooni.utils.legacy import start_legacy_test, adapt_legacy_test

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
            log.debug("Detected TestCase %s" % val)
            classes.append(val)
        elif isLegacyTest(val):
            log.debug("Detected Legacy Test %s" % val)
            classes.append(adapt_legacy_test(val, config))
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

def processTestOptions(cls, config):
    """
    Process the parameters and :class:`twisted.python.usage.Options` of a
    :class:`ooni.nettest.Nettest`.

    :param cls:
        An subclass of :class:`ooni.nettest.TestCase`.
    :param config:
        A configured and instantiated :class:`twisted.python.usage.Options`
        class.
    """
    if cls.optParameters or cls.inputFile:
        if not cls.optParameters:
            cls.optParameters = []

        if cls.inputFile:
            cls.optParameters.append(cls.inputFile)

        class Options(usage.Options):
            optParameters = cls.optParameters

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
            return cls, options
        """

        return cls, cls.localOptions

def loadTestsAndOptions(classes, config):
    """
    Takes a list of test classes and returns their testcases and options.
    Legacy tests will be adapted.
    """
    methodPrefix = 'test'
    suiteFactory = InputTestSuite
    options = []
    testCases = []
    names = []

    _old_class_type = LegacyOONITest

    for cls in classes:
        if isinstance(cls, _old_class_type):
            try:
                cases = start_legacy_test(cls)
                testCases.append(cases)
            except Exception, e:
                log.err(e)
            else:
                try:
                    opts = cls.local_options
                    options.append(opts)
                except AttributeError, ae:
                    options.append([])
                    log.err(ae)
            if cases:
                print cases
                return [], []
        else:
            tests = reflect.prefixedMethodNames(cls, methodPrefix)
            if tests:
                cases = makeTestCases(cls, tests, methodPrefix)
                testCases.append(cases)
            try:
                #c = cls()
                #cls, opts = processTestOptions(cls, config)
                opts = processTestOptions(cls, config)
            except AttributeError, ae:
                options.append([])
                log.err(ae)
            else:
                try:
                    instance = cls()
                    inputs = instance.__get_inputs__()
                except Exception, e:
                    log.err(e)
                else:
                    opts.update(inputs)
                options.append(opts)

    log.debug("runner.loadTestsAndOptions: OPTIONS: %s" % options)
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

    def runWithInputUnit(self, inputUnit):
        idx = 0
        result = self.reporterFactory.create()

        for inputs in inputUnit:
            result.reporterFactory = self.reporterFactory

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

        result.done()

    def run(self):
        self.reporterFactory.options = self.options
        for inputUnit in InputUnitFactory(self.inputs):
            self.runWithInputUnit(inputUnit)

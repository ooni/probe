import os
import sys
import types
import time
import inspect

from twisted.internet import defer, reactor
from twisted.python import reflect, log, failure
from twisted.trial import unittest
from twisted.trial.runner import TrialRunner, TestLoader
from twisted.trial.runner import isPackage, isTestCase, ErrorHolder
from twisted.trial.runner import filenameToModule, _importFromFile

from ooni.reporter import ReporterFactory
from ooni.input import InputUnitFactory
from ooni.nettest import InputTestSuite
from ooni import nettest
from ooni.plugoo import tests as oonitests

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
        if issubclass(obj, oonitests.OONITest) and not obj == oonitests.OONITest:
                return True
        else:
            return False
    except TypeError:
        return False

def adaptLegacyTest(obj, inputs=[None]):
    """
    We take a legacy OONITest class and convert it into a nettest.TestCase.
    This allows backward compatibility of old OONI tests.

    XXX perhaps we could implement another extra layer that makes the even
    older test cases compatible with the new OONI.
    """
    class LegacyOONITest(nettest.TestCase):
        inputs = [None]
        original_test = obj

        @defer.inlineCallbacks
        def test_start_legacy_test(self):
            print "bla bla bla"
            print self.original_test
            my_test = self.original_test(None, None, None)
            yield my_test.startTest(self.input)

    return LegacyOONITest


def findTestClassesFromFile(filename):
    classes = []

    print "FILENAME %s" % filename
    module = filenameToModule(filename)
    for name, val in inspect.getmembers(module):
        if isTestCase(val):
            classes.append(val)
        elif isLegacyTest(val):
            classes.append(adaptLegacyTest(val))
    return classes

def makeTestCases(klass, tests, methodPrefix):
    cases = []
    for test in tests:
        cases.append(klass(methodPrefix+test))
    return cases

def loadTestsAndOptions(classes):
    methodPrefix = 'test'
    suiteFactory = InputTestSuite
    options = []
    testCases = []
    for klass in classes:
        try:
            k = klass()
            options.append(k.getOptions())
        except AttributeError:
            options.append([])

        tests = reflect.prefixedMethodNames(klass, methodPrefix)
        if tests:
            cases = makeTestCases(klass, tests, methodPrefix)
            testCases.append(cases)
        else:
            options.pop()

    return testCases, options

class ORunner(object):
    def __init__(self, cases, options=None):
        self.baseSuite = InputTestSuite
        self.cases = cases
        self.options = options
        self.inputs = options['inputs']
        self.reporterFactory = ReporterFactory(open('foo.log', 'a+'),
                testSuite=self.baseSuite(self.cases))

    def runWithInputUnit(self, inputUnit):
        idx = 0
        result = self.reporterFactory.create()
        for input in inputUnit:
            suite = self.baseSuite(self.cases)
            suite.input = input
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
        self.reporterFactory.writeHeader()

        for inputUnit in InputUnitFactory(self.inputs):
            self.runWithInputUnit(inputUnit)



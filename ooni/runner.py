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
from ooni import nettest
from ooni.plugoo import tests as oonitests

def isLegacyTest(obj):
    """
    Returns True if the test in question is written using the OONITest legacy
    class.
    We do this for backward compatibility of the OONIProbe API.
    """
    try:
        return issubclass(obj, oonitests.OONITest)
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
        inputs = [1]
        original_test = obj

        def test_start_legacy_test(self):
            print "bla bla bla"
            my_test = self.original_test()
            print my_test
            print "foobat"
            my_test.startTest(self.input)
            print "HHAHAHA"

    return LegacyOONITest


class LoggedSuite(nettest.TestSuite):
    """
    Any errors logged in this suite will be reported to the L{TestResult}
    object.
    """

    def run(self, result):
        """
        Run the suite, storing all errors in C{result}. If an error is logged
        while no tests are running, then it will be added as an error to
        C{result}.

        @param result: A L{TestResult} object.
        """
        observer = unittest._logObserver
        observer._add()
        super(LoggedSuite, self).run(result)
        observer._remove()
        for error in observer.getErrors():
            result.addError(TestHolder(NOT_IN_TEST), error)
        observer.flushErrors()


class OONISuite(nettest.TestSuite):
    """
    Suite to wrap around every single test in a C{trial} run. Used internally
    by OONI to set up things necessary for OONI tests to work, regardless of
    what context they are run in.
    """

    def __init__(self, tests=()):
        suite = LoggedSuite(tests)
        super(OONISuite, self).__init__([suite])

    def _bail(self):
        from twisted.internet import reactor
        d = defer.Deferred()
        reactor.addSystemEventTrigger('after', 'shutdown',
                                      lambda: d.callback(None))
        reactor.fireSystemEvent('shutdown') # radix's suggestion
        # As long as TestCase does crap stuff with the reactor we need to
        # manually shutdown the reactor here, and that requires util.wait
        # :(
        # so that the shutdown event completes
        nettest.TestCase('mktemp')._wait(d)

    def run(self, result):
        try:
            nettest.TestSuite.run(self, result)
        finally:
            self._bail()


class NetTestLoader(TestLoader):
    """
    Reponsible for finding the modules that can work as tests and running them.
    If we detect that a certain test is written using the legacy OONI API we
    will wrap it around a next gen class to make it work here too.

    XXX This class needs to be cleaned up a *lot* of all the things we actually
    don't need.
    """
    methodPrefix = 'test'
    modulePrefix = 'test_'

    def __init__(self):
        self.suiteFactory = nettest.TestSuite
        self._importErrors = []

    def findTestClasses(self, module):
        classes = []
        for name, val in inspect.getmembers(module):
            if isTestCase(val):
                classes.append(val)
            # This is here to allow backward compatibility with legacy OONI
            # tests.
            elif isLegacyTest(val):
                print "adapting! %s" % val
                val = adaptLegacyTest(val)
                classes.append(val)
        return classes

    def loadClass(self, klass):
        """
        Given a class which contains test cases, return a sorted list of
        C{TestCase} instances.
        """
        if not (isinstance(klass, type) or isinstance(klass, types.ClassType)):
            raise TypeError("%r is not a class" % (klass,))
        if not isTestCase(klass):
            raise ValueError("%r is not a test case" % (klass,))
        names = self.getTestCaseNames(klass)
        tests = []
        for name in names:
            tests.append(self._makeCase(klass, self.methodPrefix+name))

        suite = self.suiteFactory(tests)
        print "**+*"
        print tests
        print "**+*"

        return suite
    loadTestsFromTestCase = loadClass

    def findAllInputs(self, thing):
        testClasses = self.findTestClasses(thing)
        # XXX will there ever be more than 1 test class with inputs?
        for klass in testClasses:
            try:
                inputs = klass.inputs
            except:
                pass
        return inputs

    def loadByNamesWithInput(self, names, recurse=False):
        """
        Construct a OONITestSuite containing all the tests found in 'names', where
        names is a list of fully qualified python names and/or filenames. The
        suite returned will have no duplicate tests, even if the same object
        is named twice.

        This test suite will have set the attribute inputs to the inputs found
        inside of the tests.
        """
        inputs = []
        things = []
        errors = []
        for name in names:
            try:
                thing = self.findByName(name)
                things.append(thing)
            except:
                errors.append(ErrorHolder(name, failure.Failure()))
        suites = []
        for thing in self._uniqueTests(things):
            inputs.append(self.findAllInputs(thing))
            suite = self.loadAnything(thing, recurse)
            suites.append(suite)

        suites.extend(errors)
        return inputs, suites

class OONIRunner(object):
    """
    A specialised runner that is used by the ooniprobe frontend to run tests.
    Heavily inspired by the trial TrialRunner class.
    """

    DEBUG = 'debug'
    DRY_RUN = 'dry-run'

    def _getDebugger(self):
        dbg = pdb.Pdb()
        try:
            import readline
        except ImportError:
            print "readline module not available"
            sys.exc_clear()
        for path in ('.pdbrc', 'pdbrc'):
            if os.path.exists(path):
                try:
                    rcFile = file(path, 'r')
                except IOError:
                    sys.exc_clear()
                else:
                    dbg.rcLines.extend(rcFile.readlines())
        return dbg


    def _setUpTestdir(self):
        self._tearDownLogFile()
        currentDir = os.getcwd()
        base = filepath.FilePath(self.workingDirectory)
        testdir, self._testDirLock = util._unusedTestDirectory(base)
        os.chdir(testdir.path)
        return currentDir


    def _tearDownTestdir(self, oldDir):
        os.chdir(oldDir)
        self._testDirLock.unlock()


    _log = log
    def _makeResult(self):
        reporter = self.reporterFactory(self.stream, self.tbformat,
                                        self.rterrors, self._log)
        if self.uncleanWarnings:
            reporter = UncleanWarningsReporterWrapper(reporter)
        return reporter

    def __init__(self, reporterFactory,
                 reportfile="report.yaml",
                 mode=None,
                 logfile='test.log',
                 stream=sys.stdout,
                 profile=False,
                 tracebackFormat='default',
                 realTimeErrors=False,
                 uncleanWarnings=False,
                 workingDirectory=None,
                 forceGarbageCollection=False):
        self.reporterFactory = reporterFactory
        self._reportfile = reportfile
        self.logfile = logfile
        self.mode = mode
        self.stream = stream
        self.tbformat = tracebackFormat
        self.rterrors = realTimeErrors
        self.uncleanWarnings = uncleanWarnings
        self._result = None
        self.workingDirectory = workingDirectory or '_trial_temp'
        self._logFileObserver = None
        self._logFileObject = None
        self._forceGarbageCollection = forceGarbageCollection
        if profile:
            self.run = util.profiled(self.run, 'profile.data')

    def _tearDownLogFile(self):
        if self._logFileObserver is not None:
            log.removeObserver(self._logFileObserver.emit)
            self._logFileObserver = None
        if self._logFileObject is not None:
            self._logFileObject.close()
            self._logFileObject = None

    def _setUpLogFile(self):
        self._tearDownLogFile()
        if self.logfile == '-':
            logFile = sys.stdout
        else:
            logFile = file(self.logfile, 'a')
        self._logFileObject = logFile
        self._logFileObserver = log.FileLogObserver(logFile)
        log.startLoggingWithObserver(self._logFileObserver.emit, 0)

    def run(self, tests, inputs=[None]):
        """
        Run the test or suite and return a result object.
        """
        reporterFactory = ReporterFactory(open(self._reportfile, 'a+'),
                testSuite=tests)
        reporterFactory.writeHeader()
        for inputUnit in InputUnitFactory(inputs):
            testSuiteFactory = nettest.TestSuiteFactory(inputUnit, tests, nettest.TestSuite)
            testUnitReport = reporterFactory.create()
            for suite in testSuiteFactory:
                suite(testUnitReport)
            testUnitReport.done()


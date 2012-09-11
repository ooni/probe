import types
import time
import inspect

from twisted.internet import defer
from twisted.trial import unittest
from twisted.trial.runner import TrialRunner, TestLoader
from twisted.trial.runner import isPackage, isTestCase

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

def adaptLegacyTest(obj):
    """
    We take a legacy OONITest class and convert it into a nettest.TestCase.
    This allows backward compatibility of old OONI tests.

    XXX perhaps we could implement another extra layer that makes the even
    older test cases compatible with the new OONI.
    """
    class LegacyOONITest(nettest.TestCase):
        pass


class LoggedSuite(nettest.TestSuite):
    """
    Any errors logged in this suite will be reported to the L{TestResult}
    object.
    """

    def run(self, result, input):
        """
        Run the suite, storing all errors in C{result}. If an error is logged
        while no tests are running, then it will be added as an error to
        C{result}.

        @param result: A L{TestResult} object.
        """
        observer = unittest._logObserver
        observer._add()
        super(LoggedSuite, self).run(result, input)
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

    def run(self, result, input):
        try:
            nettest.TestSuite.run(self, result, input)
        finally:
            self._bail()


class OONIRunner(TrialRunner):
    def run(self, test):
        return TrialRunner.run(self, test)

    def _runWithoutDecoration(self, test):
        """
        Private helper that runs the given test but doesn't decorate it.
        """
        result = self._makeResult()
        # decorate the suite with reactor cleanup and log starting
        # This should move out of the runner and be presumed to be
        # present
        suite = OONISuite([test])
        print "HERE IS THE TEST:"
        print test
        print "-------------"
        try:
            inputs = test.inputs
        except:
            inputs = [None]

        startTime = time.time()
        if self.mode == self.DRY_RUN:
            for single in nettest._iterateTests(suite):
                input = None
                if type(single) == type(tuple()):
                    single, input = single
                result.startTest(single, input)
                result.addSuccess(single)
                result.stopTest(single)
        else:
            if self.mode == self.DEBUG:
                # open question - should this be self.debug() instead.
                debugger = self._getDebugger()
                run = lambda x: debugger.runcall(suite.run, result, x)
            else:
                run = lambda x: suite.run(result, x)

            oldDir = self._setUpTestdir()
            try:
                self._setUpLogFile()
                # XXX work on this better
                for input in inputs:
                    run(input)
            finally:
                self._tearDownLogFile()
                self._tearDownTestdir(oldDir)

        endTime = time.time()
        done = getattr(result, 'done', None)
        if done is None:
            warnings.warn(
                "%s should implement done() but doesn't. Falling back to "
                "printErrors() and friends." % reflect.qual(result.__class__),
                category=DeprecationWarning, stacklevel=3)
            result.printErrors()
            result.writeln(result.separator)
            result.writeln('Ran %d tests in %.3fs', result.testsRun,
                           endTime - startTime)
            result.write('\n')
            result.printSummary()
        else:
            result.done()
        return result


class TestLoader(TestLoader):
    """
    Reponsible for finding the modules that can work as tests and running them.
    If we detect that a certain test is written using the legacy OONI API we
    will wrap it around a next gen class to make it work here too.
    """
    def __init__(self):
        super(TestLoader, self).__init__()
        self.suiteFactory = nettest.TestSuite

    def findTestClasses(self, module):
        classes = []
        for name, val in inspect.getmembers(module):
            if isTestCase(val):
                classes.append(val)
            # This is here to allow backward compatibility with legacy OONI
            # tests.
            elif isLegacyTest(val):
                #val = adaptLegacyTest(val)
                classes.append(val)
        return self.sort(classes)
        #return runner.TestLoader.findTestClasses(self, module)



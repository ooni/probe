import os
import sys
import types
import time
import inspect

from twisted.internet import defer
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


class NetTestLoader(object):
    """
    Reponsible for finding the modules that can work as tests and running them.
    If we detect that a certain test is written using the legacy OONI API we
    will wrap it around a next gen class to make it work here too.
    """
    methodPrefix = 'test'
    modulePrefix = 'test_'

    def __init__(self):
        self.suiteFactory = nettest.TestSuite
        self._importErrors = []


    def findTestClasses(self, module):
        classes = []
        for name, val in inspect.getmembers(module):
            try:
                inputs = val.inputs
            except:
                inputs = None
            if isTestCase(val):
                classes.append((val, inputs))
            # This is here to allow backward compatibility with legacy OONI
            # tests.
            elif isLegacyTest(val):
                #val = adaptLegacyTest(val)
                classes.append((val, inputs))
        return classes

    def findByName(self, name):
        """
        Return a Python object given a string describing it.

        @param name: a string which may be either a filename or a
        fully-qualified Python name.

        @return: If C{name} is a filename, return the module. If C{name} is a
        fully-qualified Python name, return the object it refers to.
        """
        if os.path.exists(name):
            return filenameToModule(name)
        return reflect.namedAny(name)


    def loadModule(self, module):
        """
        Return a test suite with all the tests from a module.

        Included are TestCase subclasses and doctests listed in the module's
        __doctests__ module. If that's not good for you, put a function named
        either C{testSuite} or C{test_suite} in your module that returns a
        TestSuite, and I'll use the results of that instead.

        If C{testSuite} and C{test_suite} are both present, then I'll use
        C{testSuite}.
        """
        ## XXX - should I add an optional parameter to disable the check for
        ## a custom suite.
        ## OR, should I add another method
        if not isinstance(module, types.ModuleType):
            raise TypeError("%r is not a module" % (module,))
        if hasattr(module, 'testSuite'):
            return module.testSuite()
        elif hasattr(module, 'test_suite'):
            return module.test_suite()

        suite = self.suiteFactory()
        for testClass, inputs in self.findTestClasses(module):
            testCases = self.loadClass(testClass)

        return testCases
    loadTestsFromModule = loadModule

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
        suite.inputs = klass.inputs
        return suite
    loadTestsFromTestCase = loadClass

    def getTestCaseNames(self, klass):
        """
        Given a class that contains C{TestCase}s, return a list of names of
        methods that probably contain tests.
        """
        return reflect.prefixedMethodNames(klass, self.methodPrefix)

    def loadMethod(self, method):
        """
        Given a method of a C{TestCase} that represents a test, return a
        C{TestCase} instance for that test.
        """
        if not isinstance(method, types.MethodType):
            raise TypeError("%r not a method" % (method,))
        return self._makeCase(method.im_class, _getMethodNameInClass(method))

    def _makeCase(self, klass, methodName):
        return klass(methodName)

    def loadPackage(self, package, recurse=False):
        """
        Load tests from a module object representing a package, and return a
        TestSuite containing those tests.

        Tests are only loaded from modules whose name begins with 'test_'
        (or whatever C{modulePrefix} is set to).

        @param package: a types.ModuleType object (or reasonable facsimilie
        obtained by importing) which may contain tests.

        @param recurse: A boolean.  If True, inspect modules within packages
        within the given package (and so on), otherwise, only inspect modules
        in the package itself.

        @raise: TypeError if 'package' is not a package.

        @return: a TestSuite created with my suiteFactory, containing all the
        tests.
        """
        if not isPackage(package):
            raise TypeError("%r is not a package" % (package,))
        pkgobj = modules.getModule(package.__name__)
        if recurse:
            discovery = pkgobj.walkModules()
        else:
            discovery = pkgobj.iterModules()
        discovered = []
        for disco in discovery:
            if disco.name.split(".")[-1].startswith(self.modulePrefix):
                discovered.append(disco)
        suite = self.suiteFactory()
        for modinfo in self.sort(discovered):
            try:
                module = modinfo.load()
            except:
                thingToAdd = ErrorHolder(modinfo.name, failure.Failure())
            else:
                thingToAdd = self.loadModule(module)
            suite.addTest(thingToAdd)
        return suite

    def loadDoctests(self, module):
        """
        Return a suite of tests for all the doctests defined in C{module}.

        @param module: A module object or a module name.
        """
        if isinstance(module, str):
            try:
                module = reflect.namedAny(module)
            except:
                return ErrorHolder(module, failure.Failure())
        if not inspect.ismodule(module):
            warnings.warn("trial only supports doctesting modules")
            return
        extraArgs = {}
        if sys.version_info > (2, 4):
            # Work around Python issue2604: DocTestCase.tearDown clobbers globs
            def saveGlobals(test):
                """
                Save C{test.globs} and replace it with a copy so that if
                necessary, the original will be available for the next test
                run.
                """
                test._savedGlobals = getattr(test, '_savedGlobals', test.globs)
                test.globs = test._savedGlobals.copy()
            extraArgs['setUp'] = saveGlobals
        return doctest.DocTestSuite(module, **extraArgs)

    def loadAnything(self, thing, recurse=False):
        """
        Given a Python object, return whatever tests that are in it. Whatever
        'in' might mean.

        @param thing: A Python object. A module, method, class or package.
        @param recurse: Whether or not to look in subpackages of packages.
        Defaults to False.

        @return: A C{TestCase} or C{TestSuite}.
        """
        print "Loading anything! %s" % thing
        ret = None
        if isinstance(thing, types.ModuleType):
            if isPackage(thing):
                ret = self.loadPackage(thing, recurse)
            ret = self.loadModule(thing)
        elif isinstance(thing, types.ClassType):
            ret = self.loadClass(thing)
        elif isinstance(thing, type):
            ret = self.loadClass(thing)
        elif isinstance(thing, types.MethodType):
            ret = self.loadMethod(thing)
        if not ret:
            raise TypeError("No loader for %r. Unrecognized type" % (thing,))
        try:
            ret.inputs = ret.inputs
        except:
            ret.inputs = [None]
        return ret

    def loadByName(self, name, recurse=False):
        """
        Given a string representing a Python object, return whatever tests
        are in that object.

        If C{name} is somehow inaccessible (e.g. the module can't be imported,
        there is no Python object with that name etc) then return an
        L{ErrorHolder}.

        @param name: The fully-qualified name of a Python object.
        """
        print "Load by Name!"
        try:
            thing = self.findByName(name)
        except:
            return ErrorHolder(name, failure.Failure())
        return self.loadAnything(thing, recurse)
    loadTestsFromName = loadByName

    def loadByNames(self, names, recurse=False):
        """
        Construct a TestSuite containing all the tests found in 'names', where
        names is a list of fully qualified python names and/or filenames. The
        suite returned will have no duplicate tests, even if the same object
        is named twice.
        """
        print "Load by Names!"
        things = []
        errors = []
        for name in names:
            try:
                things.append(self.findByName(name))
            except:
                errors.append(ErrorHolder(name, failure.Failure()))
        suites = [self.loadAnything(thing, recurse)
                  for thing in self._uniqueTests(things)]
        suites.extend(errors)
        return suites
        #return self.suiteFactory(suites)


    def _uniqueTests(self, things):
        """
        Gather unique suite objects from loaded things. This will guarantee
        uniqueness of inherited methods on TestCases which would otherwise hash
        to same value and collapse to one test unexpectedly if using simpler
        means: e.g. set().
        """
        entries = []
        for thing in things:
            if isinstance(thing, types.MethodType):
                entries.append((thing, thing.im_class))
            else:
                entries.append((thing,))
        return [entry[0] for entry in set(entries)]


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

    def run(self, test):
        """
        Run the test or suite and return a result object.
        """
        print test
        inputs = test.inputs
        reporterFactory = ReporterFactory(open(self._reportfile, 'a+'),
                testSuite=test)
        reporterFactory.writeHeader()
        #testUnitReport = OONIReporter(open('reporting.log', 'a+'))
        #testUnitReport.writeHeader(FooTest)
        for inputUnit in InputUnitFactory(inputs):
            testUnitReport = reporterFactory.create()
            test(testUnitReport, inputUnit)
            testUnitReport.done()

    def _runWithInput(self, test, input):
        """
        Private helper that runs the given test with the given input.
        """
        result = self._makeResult()
        # decorate the suite with reactor cleanup and log starting
        # This should move out of the runner and be presumed to be
        # present
        suite = TrialSuite([test])
        startTime = time.time()

        ## XXX replace this with the actual way of running the test.
        run = lambda: suite.run(result)

        oldDir = self._setUpTestdir()
        try:
            self._setUpLogFile()
            run()
        finally:
            self._tearDownLogFile()
            self._tearDownTestdir(oldDir)

        endTime = time.time()
        done = getattr(result, 'done', None)
        result.done()
        return result



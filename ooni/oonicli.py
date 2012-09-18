#!/usr/bin/env python
# -*- coding: UTF-8
#
#    oonicli
#    *********
#
#    oonicli is the next generation ooniprober. It based off of twisted's trial
#    unit testing framework.
#
#    :copyright: (c) 2012 by Arturo Filastò
#    :license: see LICENSE for more details.
#
#    original copyright (c) by Twisted Matrix Laboratories.


import sys, os, random, gc, time, warnings

from twisted.internet import defer
from twisted.application import app
from twisted.python import usage, reflect, failure
from twisted.python.filepath import FilePath
from twisted import plugin
from twisted.python.util import spewer
from twisted.python.compat import set
from twisted.trial import itrial
from ooni import runner, reporter


def _parseLocalVariables(line):
    """
    Accepts a single line in Emacs local variable declaration format and
    returns a dict of all the variables {name: value}.
    Raises ValueError if 'line' is in the wrong format.

    See http://www.gnu.org/software/emacs/manual/html_node/File-Variables.html
    """
    paren = '-*-'
    start = line.find(paren) + len(paren)
    end = line.rfind(paren)
    if start == -1 or end == -1:
        raise ValueError("%r not a valid local variable declaration" % (line,))
    items = line[start:end].split(';')
    localVars = {}
    for item in items:
        if len(item.strip()) == 0:
            continue
        split = item.split(':')
        if len(split) != 2:
            raise ValueError("%r contains invalid declaration %r"
                             % (line, item))
        localVars[split[0].strip()] = split[1].strip()
    return localVars


def loadLocalVariables(filename):
    """
    Accepts a filename and attempts to load the Emacs variable declarations
    from that file, simulating what Emacs does.

    See http://www.gnu.org/software/emacs/manual/html_node/File-Variables.html
    """
    f = file(filename, "r")
    lines = [f.readline(), f.readline()]
    f.close()
    for line in lines:
        try:
            return _parseLocalVariables(line)
        except ValueError:
            pass
    return {}


def getTestModules(filename):
    testCaseVar = loadLocalVariables(filename).get('test-case-name', None)
    if testCaseVar is None:
        return []
    return testCaseVar.split(',')


def isTestFile(filename):
    """
    Returns true if 'filename' looks like a file containing unit tests.
    False otherwise.  Doesn't care whether filename exists.
    """
    basename = os.path.basename(filename)
    return (basename.startswith('test_')
            and os.path.splitext(basename)[1] == ('.py'))


class Options(usage.Options, app.ReactorSelectionMixin):
    synopsis = """%s [options] [[file|package|module|TestCase|testmethod]...]
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                "network tests. These are loaded from modules, packages and"
                "files listed on the command line")

    optFlags = [["help", "h"],
                ["rterrors", "e", "realtime errors, print out tracebacks as "
                 "soon as they occur"],
                ["debug", "b", "Run tests in the Python debugger. Will load "
                 "'.pdbrc' from current directory if it exists."],
                ["debug-stacktraces", "B", "Report Deferred creation and "
                 "callback stack traces"],
                ["nopm", None, "don't automatically jump into debugger for "
                 "postmorteming of exceptions"],
                ["dry-run", 'n', "do everything but run the tests"],
                ["force-gc", None, "Have OONI run gc.collect() before and "
                 "after each test case."],
                ["profile", None, "Run tests under the Python profiler"],
                ["unclean-warnings", None,
                 "Turn dirty reactor errors into warnings"],
                ["no-recurse", "N", "Don't recurse into packages"],
                ['help-reporters', None,
                 "Help on available output plugins (reporters)"]
                ]

    optParameters = [
        ["logfile", "l", "test.log", "log file name"],
        ["random", "z", None,
         "Run tests in random order using the specified seed"],
        ['temp-directory', None, '_trial_temp',
         'Path to use as working directory for tests.'],
        ['reporter', None, 'default',
         'The reporter to use for this test run.  See --help-reporters for '
         'more info.']]

    compData = usage.Completions(
        optActions={"tbformat": usage.CompleteList(["plain", "emacs", "cgitb"]),
                    "logfile": usage.CompleteFiles(descr="log file name"),
                    "random": usage.Completer(descr="random seed")},
        extraActions=[usage.CompleteFiles(
                "*.py", descr="file | module | package | TestCase | testMethod",
                repeat=True)],
        )

    fallbackReporter = reporter.OONIReporter
    tracer = None

    def __init__(self):
        self['tests'] = set()
        usage.Options.__init__(self)


    def coverdir(self):
        """
        Return a L{FilePath} representing the directory into which coverage
        results should be written.
        """
        coverdir = 'coverage'
        result = FilePath(self['temp-directory']).child(coverdir)
        print "Setting coverage directory to %s." % (result.path,)
        return result


    def opt_coverage(self):
        """
        Generate coverage information in the I{coverage} file in the
        directory specified by the I{trial-temp} option.
        """
        import trace
        self.tracer = trace.Trace(count=1, trace=0)
        sys.settrace(self.tracer.globaltrace)


    def opt_testmodule(self, filename):
        """
        Filename to grep for test cases (-*- test-case-name)
        """
        # If the filename passed to this parameter looks like a test module
        # we just add that to the test suite.
        #
        # If not, we inspect it for an Emacs buffer local variable called
        # 'test-case-name'.  If that variable is declared, we try to add its
        # value to the test suite as a module.
        #
        # This parameter allows automated processes (like Buildbot) to pass
        # a list of files to OONI with the general expectation of "these files,
        # whatever they are, will get tested"
        if not os.path.isfile(filename):
            sys.stderr.write("File %r doesn't exist\n" % (filename,))
            return
        filename = os.path.abspath(filename)
        if isTestFile(filename):
            self['tests'].add(filename)
        else:
            self['tests'].update(getTestModules(filename))


    def opt_spew(self):
        """
        Print an insanely verbose log of everything that happens.  Useful
        when debugging freezes or locks in complex code.
        """
        sys.settrace(spewer)


    def opt_help_reporters(self):
        synopsis = ("OONI's output can be customized using plugins called "
                    "Reporters. You can\nselect any of the following "
                    "reporters using --reporter=<foo>\n")
        print synopsis
        for p in plugin.getPlugins(itrial.IReporter):
            print '   ', p.longOpt, '\t', p.description
        print
        sys.exit(0)


    def opt_disablegc(self):
        """
        Disable the garbage collector
        """
        gc.disable()


    def opt_tbformat(self, opt):
        """
        Specify the format to display tracebacks with. Valid formats are
        'plain', 'emacs', and 'cgitb' which uses the nicely verbose stdlib
        cgitb.text function
        """
        try:
            self['tbformat'] = TBFORMAT_MAP[opt]
        except KeyError:
            raise usage.UsageError(
                "tbformat must be 'plain', 'emacs', or 'cgitb'.")


    def opt_recursionlimit(self, arg):
        """
        see sys.setrecursionlimit()
        """
        try:
            sys.setrecursionlimit(int(arg))
        except (TypeError, ValueError):
            raise usage.UsageError(
                "argument to recursionlimit must be an integer")


    def opt_random(self, option):
        try:
            self['random'] = long(option)
        except ValueError:
            raise usage.UsageError(
                "Argument to --random must be a positive integer")
        else:
            if self['random'] < 0:
                raise usage.UsageError(
                    "Argument to --random must be a positive integer")
            elif self['random'] == 0:
                self['random'] = long(time.time() * 100)


    def opt_without_module(self, option):
        """
        Fake the lack of the specified modules, separated with commas.
        """
        for module in option.split(","):
            if module in sys.modules:
                warnings.warn("Module '%s' already imported, "
                              "disabling anyway." % (module,),
                              category=RuntimeWarning)
            sys.modules[module] = None


    def parseArgs(self, *args):
        self['tests'].update(args)


    def postOptions(self):
        # Only load reporters now, as opposed to any earlier, to avoid letting
        # application-defined plugins muck up reactor selecting by importing
        # t.i.reactor and causing the default to be installed.
        self['reporter'] = reporter.OONIReporter

        if 'tbformat' not in self:
            self['tbformat'] = 'default'
        if self['nopm']:
            if not self['debug']:
                raise usage.UsageError("you must specify --debug when using "
                                       "--nopm ")
            failure.DO_POST_MORTEM = False



def _initialDebugSetup(config):
    # do this part of debug setup first for easy debugging of import failures
    if config['debug']:
        failure.startDebugMode()
    if config['debug'] or config['debug-stacktraces']:
        defer.setDebugging(True)



def _getSuite(config):
    loader = _getLoader(config)
    recurse = not config['no-recurse']
    print "loadByNames %s" % config['tests']
    return loader.loadByNames(config['tests'], recurse)


def _getLoader(config):
    loader = runner.TestLoader()
    if config['random']:
        randomer = random.Random()
        randomer.seed(config['random'])
        loader.sorter = lambda x : randomer.random()
        print 'Running tests shuffled with seed %d\n' % config['random']
    return loader



def _makeRunner(config):
    mode = None
    if config['debug']:
        mode = runner.OONIRunner.DEBUG
    if config['dry-run']:
        mode = runner.OONIRunner.DRY_RUN
    print "using %s" % config['reporter']
    return runner.OONIRunner(config['reporter'],
                              mode=mode,
                              profile=config['profile'],
                              logfile=config['logfile'],
                              tracebackFormat=config['tbformat'],
                              realTimeErrors=config['rterrors'],
                              uncleanWarnings=config['unclean-warnings'],
                              workingDirectory=config['temp-directory'],
                              forceGarbageCollection=config['force-gc'])


if 0:
    loader = runner.TestLoader()
    loader.suiteFactory = TestSuite

    for inputUnit in InputUnitFactory(FooTest.inputs):
        print inputUnit

    suite = loader.loadClass(FooTest)

    reporterFactory = ReporterFactory(open('reporting.log', 'a+'), testSuite=suite)
    reporterFactory.writeHeader()
    #testUnitReport = OONIReporter(open('reporting.log', 'a+'))
    #testUnitReport.writeHeader(FooTest)
    for inputUnit in InputUnitFactory(FooTest.inputs):
        testUnitReport = reporterFactory.create()
        suite(testUnitReport, inputUnit)
        testUnitReport.done()

def run():
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    config = Options()
    try:
        config.parseOptions()
    except usage.error, ue:
        raise SystemExit, "%s: %s" % (sys.argv[0], ue)
    _initialDebugSetup(config)
    trialRunner = _makeRunner(config)
    suite = _getSuite(config)
    print suite
    test_result = trialRunner.run(suite)
    if config.tracer:
        sys.settrace(None)
        results = config.tracer.results()
        results.write_results(show_missing=1, summary=False,
                              coverdir=config.coverdir().path)
    sys.exit(not test_result.wasSuccessful())


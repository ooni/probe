#-*- coding: utf-8 -*-

import sys
import os
import random
import time
import yaml

from twisted.internet import defer, reactor, task
from twisted.application import app
from twisted.python import usage, failure
from twisted.python.util import spewer

from ooni import nettest, runner, reporter, config
from ooni.director import Director
from ooni.reporter import YAMLReporter, OONIBReporter

from ooni.inputunit import InputUnitFactory

from ooni.nettest import NetTestLoader, MissingRequiredOption

from ooni.utils import net
from ooni.utils import checkForRoot, NotRootError
from ooni.utils import log

class Options(usage.Options):
    synopsis = """%s [options] [path to test].py
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                " network tests. These are loaded from modules, packages and"
                " files listed on the command line")

    optFlags = [["help", "h"],
                ["resume", "r"]]

    optParameters = [["reportfile", "o", None, "report file name"],
                     ["testdeck", "i", None,
                         "Specify as input a test deck: a yaml file containig the tests to run an their arguments"],
                     ["collector", "c", None,
                         "Address of the collector of test results. (example: http://127.0.0.1:8888)"],
                     ["logfile", "l", None, "log file name"],
                     ["pcapfile", "O", None, "pcap file name"],
                     ["parallelism", "p", "10", "input parallelism"],
                     ]

    compData = usage.Completions(
        extraActions=[usage.CompleteFiles(
                "*.py", descr="file | module | package | TestCase | testMethod",
                repeat=True)],)

    tracer = None

    def __init__(self):
        self['test'] = None
        usage.Options.__init__(self)

    def opt_asciilulz(self):
        from ooni.utils import logo
        print logo.getlogo()

    def opt_spew(self):
        """
        Print an insanely verbose log of everything that happens.  Useful
        when debugging freezes or locks in complex code.
        """
        sys.settrace(spewer)

    def parseArgs(self, *args):
        if self['testdeck']:
            return
        try:
            self['test'] = args[0]
            self['subargs'] = args[1:]
        except:
            raise usage.UsageError("No test filename specified!")

def parseNetTestOptions(obj, argv):
    if not hasattr(obj.usageOptions, 'optParameters'):
        obj.usageOptions.optParameters = []

    if obj.inputFile:
        obj.usageOptions.optParameters.append(obj.inputFile)

    if obj.baseParameters:
        for parameter in obj.baseParameters:
            obj.usageOptions.optParameters.append(parameter)

    if obj.baseFlags:
        if not hasattr(obj.usageOptions, 'optFlags'):
            obj.usageOptions.optFlags = []
        for flag in obj.baseFlags:
            obj.usageOptions.optFlags.append(flag)

    options = obj.usageOptions()
    options.parseOptions(argv)

    return options

def updateStatusBar():
    for test_filename in config.state.keys():
        # The ETA is not updated so we we will not print it out for the
        # moment.
        eta = config.state[test_filename].eta()
        progress = config.state[test_filename].progress()
        progress_bar_frmt = "[%s] %s%%" % (test_filename, progress)
        log.debug(progress_bar_frmt)

def testsEnded(*arg, **kw):
    """
    You can place here all the post shutdown tasks.
    """
    log.debug("testsEnded: Finished running all tests")
    config.start_reactor = False
    try: reactor.stop()
    except: pass

def testFailed(failure):
    log.err("Failed in running a test inside a test list")
    failure.printTraceback()

def runTestList(none, test_list):
    """
    none: is always None.

    test_list (list): a list of tuples containing (test_cases, options,
        cmd_line_options)
    """
    deck_dl = []

    for test in test_list:
        test_cases, options, cmd_line_options = test
        d1 = runner.runTestCases(test_cases, options, cmd_line_options)
        deck_dl.append(d1)

    d2 = defer.DeferredList(deck_dl)
    d2.addCallback(testsEnded)
    d2.addErrback(testFailed)

    # Print every 5 second the list of current tests running
    l = task.LoopingCall(updateStatusBar)
    l.start(5.0)
    return d2

def errorRunningTests(failure):
    log.err("There was an error in running a test")
    failure.printTraceback()


def parseOptions():
    cmd_line_options = Options()
    if len(sys.argv) == 1:
        cmd_line_options.getUsage()
    try:
        cmd_line_options.parseOptions()
    except usage.UsageError, ue:
        raise SystemExit, "%s: %s" % (sys.argv[0], ue)

    return dict(cmd_line_options)

def shutdown(result):
    """
    This will get called once all the operations that need to be done in the
    current oonicli session have been completed.
    """
    reactor.stop()

def runWithDirector():
    """
    Instance the director, parse command line options and start an ooniprobe
    test!
    """
    global_options = parseOptions()
    config.cmd_line_options = global_options

    log.start(global_options['logfile'])

    net_test_args = global_options.pop('subargs')
    net_test_file = global_options['test']

    net_test_loader = NetTestLoader(net_test_file)
    options = net_test_loader.usageOptions()
    options.parseOptions(net_test_args)

    net_test_options = dict(options)

    # reporters = [YAMLReporter, OONIBReporter]

    yaml_reporter = YAMLReporter(net_test_loader.testDetails)
    reporters = [yaml_reporter]

    director = Director(reporters)
    try:
        d = director.startNetTest(net_test_loader, net_test_options)
        d.addBoth(shutdown)
        reactor.run()
    except MissingRequiredOption, option_name:
        log.err('Missing required option: "%s"' % option_name)
        print options.getUsage()

def run():
    """
    Parses command line arguments of test.
    """

    if config.privacy.includepcap:
        log.msg("Starting")
        if not config.reports.pcap:
            config.generatePcapFilename()
        runner.startSniffing()

    resume = cmd_line_options['resume']

    # contains (test_cases, options, cmd_line_options)
    test_list = []

    if cmd_line_options['testdeck']:
        test_deck = yaml.safe_load(open(cmd_line_options['testdeck']))
        for test in test_deck:
            del cmd_line_options
            cmd_line_options = test['options']
            if resume:
                cmd_line_options['resume'] = True
            else:
                cmd_line_options['resume'] = False
            test_list.append(runner.loadTest(cmd_line_options))
    else:
        log.debug("No test deck detected")
        del cmd_line_options['testdeck']
        test_list.append(runner.loadTest(cmd_line_options))

    if config.advanced.start_tor:
        log.msg("Starting Tor...")
        d = runner.startTor()
        d.addCallback(runTestList, test_list)
        d.addErrback(errorRunningTests)
    else:
        # We need to pass None as first argument because when the callback is
        # fired it will pass it's result to runTestCase.
        d = runTestList(None, test_list)
        d.addErrback(errorRunningTests)

    reactor.run()



# -*- coding: UTF-8
#
# oonicli
# -------
# In here we take care of running ooniprobe from the command
# line interface
#
# :authors: Arturo Filastò, Isis Lovecruft
# :license: see included LICENSE file


import sys
import os
import random
import time
import yaml

from twisted.internet import defer, reactor
from twisted.application import app
from twisted.python import usage, failure
from twisted.python.util import spewer

from ooni import nettest, runner, reporter, config

from ooni.inputunit import InputUnitFactory

from ooni.utils import net
from ooni.utils import checkForRoot, NotRootError
from ooni.utils import log

class Options(usage.Options):
    synopsis = """%s [options] [path to test].py
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                " network tests. These are loaded from modules, packages and"
                " files listed on the command line")

    optFlags = [["help", "h"]]

    optParameters = [["reportfile", "o", None, "report file name"],
                     ["testdeck", "i", None,
                         "Specify as input a test deck: a yaml file containig the tests to run an their arguments"],
                     ["collector", "c", None,
                         "Address of the collector of test results. (example: http://127.0.0.1:8888)"],
                     ["logfile", "l", None, "log file name"],
                     ["pcapfile", "p", None, "pcap file name"]]

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

def testsEnded(*arg, **kw):
    """
    You can place here all the post shutdown tasks.
    """
    log.debug("testsEnded: Finished running all tests")
    reactor.stop()

def runTest(cmd_line_options):
    config.cmd_line_options = cmd_line_options
    config.generateReportFilenames()

    if cmd_line_options['reportfile']:
        config.reports.yamloo = cmd_line_options['reportfile']
        config.reports.pcap = config.reports.yamloo+".pcap"

    if os.path.exists(config.reports.pcap):
        print "Report PCAP already exists with filename %s" % config.reports.pcap
        print "Renaming it to %s" % config.reports.pcap+'.old'
        os.rename(config.reports.pcap, config.reports.pcap+'.old')

    classes = runner.findTestClassesFromFile(cmd_line_options['test'])
    test_cases, options = runner.loadTestsAndOptions(classes, cmd_line_options)
    if config.privacy.includepcap:
        try:
            checkForRoot()
        except NotRootError:
            print "[!] Includepcap options requires root priviledges to run"
            print "    you should run ooniprobe as root or disable the options in ooniprobe.conf"
            sys.exit(1)

        print "Starting sniffer"
        net.capturePackets(config.reports.pcap)

    return runner.runTestCases(test_cases, options, cmd_line_options)

def run():
    """
    Call me to begin testing from a file.
    """
    cmd_line_options = Options()
    if len(sys.argv) == 1:
        cmd_line_options.getUsage()
    try:
        cmd_line_options.parseOptions()
    except usage.UsageError, ue:
        raise SystemExit, "%s: %s" % (sys.argv[0], ue)

    deck_dl = []

    log.start(cmd_line_options['logfile'])
    if cmd_line_options['testdeck']:
        test_deck = yaml.safe_load(open(cmd_line_options['testdeck']))
        for test in test_deck:
            del cmd_line_options
            cmd_line_options = test['options']
            d1 = runTest(cmd_line_options)
            deck_dl.append(d1)
    else:
        log.msg("No test deck detected")
        del cmd_line_options['testdeck']
        d1 = runTest(cmd_line_options)
        deck_dl.append(d1)

    d2 = defer.DeferredList(deck_dl)
    d2.addCallback(testsEnded)

    reactor.run()

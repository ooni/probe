#!/usr/bin/env python
# -*- coding: UTF-8
#
#    oonicli
#    *********
#
#    oonicli is the next generation ooniprober. It based off of twisted's trial
#    unit testing framework.
#
#    :copyright: (c) 2012 by Arturo Filastò, Isis Lovecruft
#    :license: see LICENSE for more details.
#
#    original copyright (c) by Twisted Matrix Laboratories.


import sys
import os
import random
import time

from twisted.internet import defer, reactor
from twisted.application import app
from twisted.python import usage, failure
from twisted.python.util import spewer

from ooni import nettest, runner, reporter, config

from ooni.inputunit import InputUnitFactory

from ooni.utils import net, checkForRoot
from ooni.utils import log


class Options(usage.Options, app.ReactorSelectionMixin):
    synopsis = """%s [options] [path to test].py
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                " network tests. These are loaded from modules, packages and"
                " files listed on the command line")

    optFlags = [["help", "h"],
                ['debug-stacktraces', 'B',
                    'Report deferred creation and callback stack traces'],]

    optParameters = [["reportfile", "o", None, "report file name"],
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
        try:
            self['test'] = args[0]
            self['subArgs'] = args[1:]
        except:
            raise usage.UsageError("No test filename specified!")

def testsEnded(*arg, **kw):
    """
    You can place here all the post shutdown tasks.
    """
    log.debug("Finished running all tests")

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

    if cmd_line_options['debug-stacktraces']:
        defer.setDebugging(True)

    yamloo_filename, pcap_filename = config.oreport_filenames()

    if cmd_line_options['reportfile']:
        yamloo_filename = cmd_line_options['reportfile']
        pcap_filename = yamloo_filename+".pcap"

    if os.path.exists(yamloo_filename):
        log.msg("Report already exists with filename %s" % yamloo_filename)
        log.msg("Renaming it to %s" % yamloo_filename+'.old')
        os.rename(yamloo_filename, yamloo_filename+'.old')
    if os.path.exists(pcap_filename):
        log.msg("Report already exists with filename %s" % pcap_filename)
        log.msg("Renaming it to %s" % pcap_filename+'.old')
        os.rename(pcap_filename, pcap_filename+'.old')

    log.start(cmd_line_options['logfile'])
    classes = runner.findTestClassesFromConfig(cmd_line_options)
    test_cases, options = runner.loadTestsAndOptions(classes, cmd_line_options)
    if config.privacy.includepcap:
        try:
            checkForRoot()
        except:
            log.err("includepcap options requires root priviledges to run")
            log.err("disable it in your ooniprobe.conf file")
            sys.exit(1)
        log.debug("Starting sniffer")
        sniffer_d = net.capturePackets(pcap_filename)

    tests_d = runner.runTestCases(test_cases, options,
            cmd_line_options, yamloo_filename)
    tests_d.addBoth(testsEnded)

    reactor.run()


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

from twisted.internet import defer
from twisted.application import app
from twisted.python import usage, failure
from twisted.python.util import spewer

from ooni import nettest, runner, reporter

from ooni.inputunit import InputUnitFactory
from ooni.reporter import ReporterFactory
from ooni.nettest import InputTestSuite
from ooni.utils import log


class Options(usage.Options, app.ReactorSelectionMixin):
    synopsis = """%s [options] [[file|package|module|TestCase|testmethod]...]
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                "network tests. These are loaded from modules, packages and"
                "files listed on the command line")

    optFlags = [["help", "h"],
                ['debug-stacktraces', 'B',
                    'Report deferred creation and callback stack traces'],
                ]

    optParameters = [
        ["reportfile", "o", None, "report file name"],
        ["logfile", "l", "test.log", "log file name"],
        ['temp-directory', None, '_ooni_temp',
         'Path to use as working directory for tests.']
        ]

    compData = usage.Completions(
        extraActions=[usage.CompleteFiles(
                "*.py", descr="file | module | package | TestCase | testMethod",
                repeat=True)],
        )

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

    def postOptions(self):
        self['reporter'] = reporter.OONIReporter


def run():
    log.start()

    if len(sys.argv) == 1:
        sys.argv.append("--help")
    config = Options()
    try:
        config.parseOptions()
    except usage.error, ue:
        raise SystemExit, "%s: %s" % (sys.argv[0], ue)

    if config['debug-stacktraces']:
        defer.setDebugging(True)

    classes = runner.findTestClassesFromConfig(config)
    casesList, options = runner.loadTestsAndOptions(classes, config)

    for idx, cases in enumerate(casesList):
        orunner = runner.ORunner(cases, options[idx], config)
        orunner.run()

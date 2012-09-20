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

import unittest
import inspect

from ooni.input import InputUnitFactory
from ooni.reporter import ReporterFactory
from ooni.nettest import InputTestSuite
from ooni.plugoo import tests
from ooni import nettest, runner, reporter

from twisted.internet import defer
from twisted.application import app
from twisted.python import usage, reflect, failure, log
from twisted.python.filepath import FilePath
from twisted import plugin
from twisted.python.util import spewer
from twisted.python.compat import set
from twisted.trial import itrial
from twisted.trial import runner as irunner

class Options(usage.Options, app.ReactorSelectionMixin):
    synopsis = """%s [options] [[file|package|module|TestCase|testmethod]...]
    """ % (os.path.basename(sys.argv[0]),)

    longdesc = ("ooniprobe loads and executes a suite or a set of suites of"
                "network tests. These are loaded from modules, packages and"
                "files listed on the command line")

    optFlags = [["help", "h"]]

    optParameters = [
        ["reportfile", "o", "report.yaml", "report file name"],
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

    def opt_spew(self):
        """
        Print an insanely verbose log of everything that happens.  Useful
        when debugging freezes or locks in complex code.
        """
        sys.settrace(spewer)

    def parseArgs(self, *args):
        try:
            self['test'] = args[0]
        except:
            raise usage.UsageError("No test filename specified!")


    def postOptions(self):
        self['reporter'] = reporter.OONIReporter


def run():
    if len(sys.argv) == 1:
        sys.argv.append("--help")
    config = Options()
    try:
        config.parseOptions()
    except usage.error, ue:
        raise SystemExit, "%s: %s" % (sys.argv[0], ue)

    classes = runner.findTestClassesFromFile(config['test'])
    casesList, options = runner.loadTestsAndOptions(classes)
    for idx, cases in enumerate(casesList):
        orunner = runner.ORunner(cases, options[idx])
        orunner.run()


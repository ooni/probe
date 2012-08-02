import os
import yaml
from zope.interface import Interface, Attribute

import logging
import itertools
from twisted.internet import reactor, defer, threads
from twisted.python import failure

from ooni.utils import log
from ooni.utils import date
from ooni.plugoo import assets, work
from ooni.plugoo.reports import Report
from ooni.plugoo.interface import ITest


class OONITest(object):
    """
    This is the base class for writing OONI Tests.

    It should be used in conjunction with the ITest Interface. It allows the
    developer to benefit from OONIs reporting system and command line argument
    parsing system.
    """
    # By default we set this to False, meaning that we don't block
    blocking = False
    reactor = None
    tool = False
    ended = False

    def __init__(self, local_options, global_options, report, ooninet=None,
            reactor=None):
        # These are the options that are read through the tests suboptions
        self.local_options = local_options
        # These are the options global to all of OONI
        self.global_options = global_options
        self.report = report
        #self.ooninet = ooninet
        self.reactor = reactor
        self.result = {}

        self.initialize()
        self.assets = self.load_assets()

    def initialize(self):
        """
        Override this method if you are interested in having some extra
        behavior when your test class is instantiated.
        """
        pass

    def load_assets(self):
        """
        This method should be overriden by the test writer to provide the logic
        for loading their assets.
        """
        return {}

    def __repr__(self):
        return "<OONITest %s %s %s>" % (self.options, self.global_options,
                                           self.assets)

    def end(self):
        """
        State that the current test should finish.
        """
        self.ended = True

    def finished(self, return_value):
        """
        The Test has finished running, we must now calculate the test runtime
        and add all time data to the report.
        """
        #self.ooninet.report(result)
        self.end_time = date.now()
        result = self.result
        result['start_time'] = str(self.start_time)
        result['end_time'] = str(self.end_time)
        result['run_time'] = str(self.end_time - self.start_time)
        result['return_value'] = return_value
        log.msg("FINISHED %s" % result)
        self.report(result)
        return result

    def _do_experiment(self, args):
        """
        A wrapper around the launch of experiment.
        If we are running a blocking test experiment will be run in a thread if
        not we expect it to return a Deferred.

        @param args: the asset line(s) that we are working on.

        returns a deferred.
        """
        if self.blocking:
            self.d = threads.deferToThread(self.experiment, args)
        else:
            self.d = self.experiment(args)

        self.d.addCallback(self.control, args)
        self.d.addCallback(self.finished)
        return self.d

    def control(self, result, args):
        """
        Run the control.

        @param result: what was returned by experiment.

        @param args: the asset(s) lines that we are working on.
        """
        log.msg("Doing control")
        return result

    def experiment(self, args):
        """
        Run the experiment. This sample implementation returns a deferred,
        making it a non-blocking test.

        @param args: the asset(s) lines that we are working on.
        """
        log.msg("Doing experiment")
        d = defer.Deferred()
        return d

    def startTest(self, args):
        """
        This method is invoked by the worker to start the test with one line of
        the asset file.

        @param args: the asset(s) lines that we are working on.
        """
        self.start_time = date.now()
        log.msg("Starting test %s" % self.__class__)
        return self._do_experiment(args)


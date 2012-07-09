import os
import yaml
from zope.interface import Interface, Attribute

import logging
import itertools
from twisted.internet import reactor, defer, threads
from twisted.python import failure

from ooni import log
from ooni import date
from ooni.plugoo import assets, work
from ooni.plugoo.reports import Report
from ooni.plugoo.interface import ITest


class OONITest(object):
    blocking = False

    def __init__(self, local_options, global_options, report, ooninet=None,
            reactor=None):
        self.local_options = local_options
        self.global_options = global_options
        self.assets = self.load_assets()
        self.report = report
        #self.ooninet = ooninet
        self.reactor = reactor
        self.initialize()
        self.result = {}

    def initialize(self):
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

    def finished(self, control):
        #self.ooninet.report(result)
        self.end_time = date.now()
        result = self.result
        result['start_time'] = str(self.start_time)
        result['end_time'] = str(self.end_time)
        result['run_time'] = str(self.end_time - self.start_time)
        result['control'] = control
        log.msg("FINISHED %s" % result)
        self.report(result)
        return result

    def _do_experiment(self, args):
        if self.blocking:
            self.d = threads.deferToThread(self.experiment, args)
        else:
            self.d = self.experiment(args)

        self.d.addCallback(self.control, args)
        self.d.addCallback(self.finished)
        return self.d

    def control(self, result, args):
        log.msg("Doing control")

        if self.blocking:
            return result

        def end(cb):
            return result
        d = defer.Deferred()
        d.addCallback(end)
        return d

    def experiment(self, args):
        log.msg("Doing experiment")
        d = defer.Deferred()
        return d

    def startTest(self, args):
        self.start_time = date.now()
        log.msg("Starting test %s" % self.__class__)
        return self._do_experiment(args)


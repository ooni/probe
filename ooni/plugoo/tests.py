import os
from datetime import datetime
import yaml
from zope.interface import Interface, Attribute

import logging
import itertools
import gevent

from twisted.internet import reactor, defer, threads
from twisted.python import failure

from ooni import log
from ooni.plugoo import assets, work
from ooni.plugoo.reports import Report
from ooni.plugoo.interface import ITest


class OONITest(object):
    blocking = False

    def __init__(self, local_options, global_options, report, ooninet=None):
        self.local_options = local_options
        self.global_options = global_options
        self.assets = self.load_assets()
        self.report = report
        #self.ooninet = ooninet

    def load_assets(self):
        """
        This method should be overriden by the test writer to provide the logic
        for loading their assets.
        """
        return {'asset': None}

    def __repr__(self):
        return "<OONITest %s %s %s>" % (self.options, self.global_options,
                                           self.assets)

    def finished(self, control):
        #self.ooninet.report(result)
        self.end_time = datetime.now()
        result = {}
        result['start_time'] = self.start_time
        result['end_time'] = self.end_time
        result['run_time'] = self.end_time - self.start_time
        result['control'] = control
        log.msg("FINISHED %s" % result)
        self.report(result)
        return result

    def _do_experiment(self, args):
        if self.blocking:
            self.d = threads.deferToThread(self.experiment, args)
        else:
            self.d = defer.maybeDeferred(self.experiment, args)

        self.d.addCallback(self.control, args)
        self.d.addCallback(self.finished)
        return self.d

    def control(self, result, args):
        log.msg("Doing control")
        return result

    def experiment(self, args):
        log.msg("Doing experiment")
        return {}

    def startTest(self, args):
        self.start_time = datetime.now()
        log.msg("Starting test %s" % self.__class__)
        return self._do_experiment(args)


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


class Test:
    """
    This is a ooni probe Test.
    Also known as a Plugoo!
    """
    def __init__(self, ooni, name="test"):
        self.config = ooni.config
        self.logger = ooni.logger
        self.name = name
        self.report = Report(ooni,
                             scp=ooni.config.report.ssh,
                             file=ooni.config.report.file,
                             tcp=ooni.config.report.tcp)


    def control(self, *a, **b):
        pass

    def experiment(self, *a, **b):
        """
        Override this method to write your own
        Plugoo.
        """
        pass

    def load_assets(self, assets, index=None):
        """
        Takes as input an array of Asset objects and
        outputs an iterator for the loaded assets.

        example:
        assets = [hostlist, portlist, requestlist]
        """
        asset_count = len(assets)
        bigsize = 0
        bigidx = 0

        if asset_count > 1:
            # If we have more than on asset we try to do some
            # optimizations as how to iterate through them by
            # picking the largest asset set as the main iterator
            # and do a cartesian product on the smaller sets
            for i, v in enumerate(assets):
                size = v.len()
                if size > bigsize:
                    bigidx, bigsize = (i, size)

            smallassets = list(assets)
            smallassets.pop(bigidx)

        i = 0
        for x in assets[bigidx]:
            if asset_count > 1:
                # XXX this will only work in python 2.6, maybe refactor?
                for comb in itertools.product(*smallassets):
                    if index and i < index:
                        i += 1
                    else:
                        yield (x,) + comb
            else:
                if index and i < index:
                    i += 1
                else:
                    yield (x)

    def run(self, assets=None, extradata=None, buffer=10, timeout=100000):
        self.logger.info("Starting %s", self.name)
        jobs = []
        if assets:
            self.logger.debug("Running through tests")

            if extradata and 'index' in extradata:
                index = extradata['index']
            else:
                index = None

            for i, data in enumerate(self.load_assets(assets, index)):
                args = {'data': data}
                if extradata:
                    args = dict(args.items()+extradata.items())
                # Append to the job queue
                jobs.append(gevent.spawn(self.experiment, **args))
                # If the buffer is full run the jobs
                if i % buffer == (buffer - 1):
                    # Run the jobs with the selected timeout
                    gevent.joinall(jobs, timeout=timeout)
                    for job in jobs:
                        #print "JOB VAL: %s" % job.value
                        self.logger.info("Writing report(s)")
                        self.report(job.value)
                        job.kill()
                    jobs = []

            if len(jobs) > 0:
                gevent.joinall(jobs, timeout=timeout)
                for job in jobs:
                    #print "JOB VAL: %s" % job.value
                    self.logger.info("Writing report(s)")
                    self.report(job.value)
                    job.kill()
                jobs = []
        else:
            self.logger.error("No Assets! Dying!")

class ITest(Interface):
    """
    This interface represents an OONI test. It fires a deferred on completion.
    """

    shortName = Attribute("""A short user facing description for this test""")
    description = Attribute("""A string containing a longer description for the test""")

    requirements = Attribute("""What is required to run this this test, for example raw socket access or UDP or TCP""")

    #deferred = Attribute("""This will be fired on test completion""")
    #node = Attribute("""This represents the node that will run the test""")
    options = Attribute("""These are the arguments to be passed to the test for it's execution""")

    blocking = Attribute("""True or False, stating if the test should be run in a thread or not.""")

    def startTest(asset):
        """
        Launches the Test with the specified arguments on a node.
        """

class TwistedTest(object):
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
        return "<TwistedTest %s %s %s>" % (self.options, self.global_options,
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


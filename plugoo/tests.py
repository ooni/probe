import os
from datetime import datetime
import yaml

import logging
import itertools
import gevent
from plugoo.reports import Report

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

            if extradata and extradata['index']:
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



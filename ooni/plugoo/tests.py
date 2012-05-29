import os
from datetime import datetime
import yaml
from zope.interface import Interface, Attribute

import logging
import itertools
import gevent
from twisted.internet import reactor, defer
from twisted.python import failure
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

    def startTest():
        """
        Launches the Test with the specified arguments on a node.
        """

#class HTTPRequestTest(HTTPClient):
class HTTPRequestTest(object):
    """
    This is an example of how I would like to be able to write a test.

    *BEWARE* this actually does not currently work, it's just an example of the
    kind of API that I am attempting to achieve to simplify the writing of
    tests.

    implements(ITest)

    """
    def startTest():
        # The response object should also contain the request
        """
        response = {'response': {'headers': ..., 'content': ...,
        'runtime': ..., 'timestamp': ...},
        'request': {'headers': ..., 'content', 'timestamp', ...}
        }
        response = self.http_request(address, headers)
        if response.headers['content'].matches("Some string"):
            self.censorship = True
            return response
        else:
            self.censorship = False
            return response

        """
        pass

class TwistedTest(object):
    def __init__(self, asset, arguments, ooninet=None):
        self.asset = asset
        self.arguments = arguments
        self.start_time = datetime.now()
        self._parse_arguments()
        #self.ooninet = ooninet

    def __repr__(self):
        return "<TwistedTest %s %s>" % (self.arguments, self.asset)

    def _parse_arguments(self):
        print self.arguments
        if self.arguments and 'test' in self.arguments:
            self.test = self.arguments['test']

    def finished(self, result):
        #self.ooninet.report(result)
        print "FINIHSED"
        self.end_time = datetime.now()
        result['start_time'] = self.start_time
        result['end_time'] = self.end_time
        result['run_time'] = self.end_time - self.start_time

    def _do_experiment(self):
        self.d = defer.maybeDeferred(self.experiment)
        self.d.addCallback(self.control)
        self.d.addCallback(self.finished)
        return self.d

    def control(self, exp):
        print "Doing control..."
        self.d.callback(result)

    def experiment(self):
        print "Doing experiment"
        self.d_experiment.callback(None)

    def startTest(self):
        print "Starting test %s" % repr(self)
        return self._do_experiment()

class TwistedTestFactory(object):

    test = None

    def __init__(self, assets, node,
                 idx=0):
        """
        """
        self.assets = assets
        self.node = node
        self.idx = idx
        self.workunit = WorkUnitFactory(assets)

    def build_test(self):
        """
        Returns a TwistedTest instance
        """
        workunit = self.workunit.next()
        t = self.test(node, workunit)
        t.factory = self
        return t


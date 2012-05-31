# -*- coding: UTF-8
"""
    work.py
    **********

    This contains all code related to generating
    Units of Work and processing it.

    :copyright: (c) 2012 by Arturo Filastò.
    :license: see LICENSE for more details.

"""
import itertools
import yaml
from datetime import datetime

from zope.interface import Interface, Attribute

from twisted.python import failure
from twisted.internet import reactor, defer

from plugoo.nodes import LocalNode

class Worker(object):
    """
    This is the core of OONI. It takes as input Work Units and
    runs them concurrently.
    """
    def __init__(self, maxconcurrent=10, reactor=reactor):
        """
        @param maxconcurrent: how many test instances should be run
                              concurrently.
        """
        self.reactor = reactor
        self.maxconcurrent = maxconcurrent
        self._running = 0
        self._queued = []

    def _run(self, r):
        """
        Check if we should start another test because we are below maximum
        concurrency.

        This function is called every time a test finishes running.

        @param r: the return value of a previous test.
        """
        if self._running > 0:
            self._running -= 1

        if self._running < self.maxconcurrent and self._queued:
            workunit, d = self._queued.pop(0)
            asset, test, idx = workunit
            while test.ended and workunit:
                try:
                    workunit, d = self._queued.pop(0)
                    asset, test, idx = workunit
                except:
                    workunit = None

            if not test.ended:
                self._running += 1
                actuald = test.startTest(asset).addBoth(self._run)

        if isinstance(r, failure.Failure):
            # XXX probably we should be doing something to retry test running
            r.trap()

        if self._running == 0 and not self._queued:
            self.reactor.stop()

        return r

    def push(self, workunit):
        """
        Add a test to the test queue and run it if we are not maxed out on
        concurrency.

        @param workunit: a tuple containing the (asset, test, idx), where asset
                         is the line of the asset(s) we are working on, test
                         is an instantiated test and idx is the index we are
                         currently at.
        """
        if self._running < self.maxconcurrent:
            asset, test, idx = workunit
            if not test.ended:
                self._running += 1
                return test.startTest(asset).addBoth(self._run)

        d = defer.Deferred()
        self._queued.append((workunit, d))
        return d

class WorkGenerator(object):
    """
    Factory responsible for creating units of work.

    This shall be run on the machine running OONI-cli. The returned WorkUnits
    can either be run locally or on a remote OONI Node or Network Node.
    """
    size = 10

    def __init__(self, test, arguments=None, start=None):
        self.Test = test

        if self.Test.assets and self.Test.assets.values()[0]:
            self.assetGenerator = itertools.product(*self.Test.assets.values())
        else:
            self.assetGenerator = None

        self.assetNames = self.Test.assets.keys()

        self.idx = 0
        self.end = False
        if start:
            self.skip(start)

    def __iter__(self):
        return self

    def skip(self, start):
        """
        Skip the first x number of lines of the asset.

        @param start: int how many items we should skip.
        """
        for j in xrange(0, start-1):
            for i in xrange(0, self.size):
                self.assetGenerator.next()
            self.idx += 1

    def next(self):
        if self.end:
            raise StopIteration

        if not self.assetGenerator:
            self.end = True
            return ({}, self.Test, self.idx)

        try:
            asset = self.assetGenerator.next()
            ret = {}
            for i, v in enumerate(asset):
                ret[self.assetNames[i]] = v
        except StopIteration:
            raise StopIteration

        self.idx += 1
        return (ret, self.Test, self.idx)


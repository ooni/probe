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

class Worker(object):
    """
    This is the core of OONI. It takes as input Work Units and
    runs them concurrently.
    """
    def __init__(self, maxconcurrent=10):
        self.maxconcurrent = maxconcurrent
        self._running = 0
        self._queued = []

    def _run(self, r):
        self._running -= 1
        if self._running < self.maxconcurrent and self._queued:
            workunit, d = self._queued.pop(0)
            asset, test, idx = workunit
            self._running += 1
            actuald = test.startTest(asset).addBoth(self._run)

        if isinstance(r, failure.Failure):
            r.trap()

        print r['start_time']
        print r['end_time']
        print r['run_time']

        if self._running == 0 and not self._queued:
            print "I am done."
            reactor.stop()

        return r

    def push(self, workunit):
        if self._running < self.maxconcurrent:
            asset, test, idx = workunit
            self._running += 1
            test.startTest(asset).addBoth(self._run)
            return
        d = defer.Deferred()
        self._queued.append((workunit, d))
        return d

class WorkUnit(object):
    """
    XXX This is currently not implemented for KISS sake.

    This is an object responsible for completing WorkUnits it will
    return its result in a deferred.

    The execution of a unit of work should be Atomic.

    Reporting to the OONI-net happens on completion of a Unit of Work.

    @Node node: This represents the node associated with the Work Unit
    @Asset asset: This is the asset associated with the Work Unit
    @Test test: This represents the Test to be with the specified assets
    @ivar arguments: These are the extra attributes to be passsed to the Test
    """

    node = None
    asset = None
    test = None
    arguments = None

    def __init__(self, asset, assetNames, test, idx):
        self.asset = asset
        if not asset:
            self.assetGenerator = iter([1])
        else:
            self.assetGenerator = iter(asset)
        self.Test = test
        self.assetNames = assetNames
        self.idx = idx

    def __iter__(self):
        return self

    def __repr__(self):
        return "<WorkUnit %s %s %s>" % (self.assetNames, self.Test, self.idx)

    def serialize(self):
        """
        Serialize this unit of work for RPC activity.
        """
        return yaml.dump(self)

    def next(self):
        """
        Launches the Unit of Work with the specified assets on the node.
        """
        try:
            asset = self.assetGenerator.next()
            ret = self.Test.set_asset(asset)
            return ret
        except StopIteration:
            raise StopIteration


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
        for j in xrange(0, start-1):
            for i in xrange(0, self.size):
                self.assetGenerator.next()
            self.idx += 1

    def next(self):
        if self.end:
            raise StopIteration

        if not self.assetGenerator:
            self.end = True
            return (self.assetNames, self.Test, self.idx)

        try:
            asset = self.assetGenerator.next()
            ret = {}
            for i, v in enumerate(asset):
                ret[self.assetNames[i]] = v
        except StopIteration:
            raise StopIteration

        self.idx += 1
        return (ret, self.Test, self.idx)

    def p_next(self):
        """
        XXX This is not used for KISS sake.
        """
        if self.end:
            raise StopIteration

        if not self.assetGenerator:
            self.end = True
            return WorkUnit(None, self.assetNames, self.Test, self.idx)

        # Plank asset
        p_asset = []
        for i in xrange(0, self.size):
            try:
                asset = self.assetGenerator.next()
                p_asset.append(asset)
                print p_asset
            except StopIteration:
                if self.asset_num > 1:
                    pass
                self.end = True
                break

        self.idx += 1
        return WorkUnit(p_asset, self.assetNames, self.Test, self.idx)


# -*- coding: UTF-8
"""
    work.py
    **********

    This contains all code related to generating
    Units of Work and processing it.

    :copyright: (c) 2012 by Arturo Filastò.
    :license: see LICENSE for more details.

"""
from datetime import datetime
import yaml

from zope.interface import Interface, Attribute

from twisted.python import failure
from twisted.internet import reactor, defer

from plugoo.nodes import LocalNode

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
        print "RUNNING"
        self._running -= 1
        if self._running < self.maxconcurrent and self._queued:
            workunit, d = self._queued.pop(0)
            for work in workunit:
                print "Going over workunits bis"
                print work
                self._running += 1
                actuald = work.startTest().addBoth(self._run)
        if isinstance(r, failure.Failure):
            r.trap()

        print "Callback fired!"
        print r['start_time']
        print r['end_time']
        print r['run_time']
        print repr(r)
        return r

    def push(self, workunit):
        print "PUSHING"
        if self._running < self.maxconcurrent:
            for work in workunit:
                print "Going over work units"
                print dir(work)
                self._running += 1
                work.startTest().addBoth(self._run)
            return
        d = defer.Deferred()
        self._queued.append((workunit, d))
        return d

class WorkUnit(object):
    """
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

    def __init__(self, node, asset, test, idx, arguments=None):
        self.asset = asset
        self.assetGenerator = iter(asset)
        self.Test = test
        self.node = node
        self.arguments = arguments
        self.idx = idx

    def __iter__(self):
        return self

    def __repr__(self):
        return "<WorkUnit %s %s %s>" % (self.arguments, self.Test, self.idx)

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
            print "Next shit.."
            print asset
            ret = self.Test(asset, self.arguments)
            print type(ret)
            print repr(ret)
            return ret
        except StopIteration:
            print "Stopped iteration!"
            raise StopIteration


class WorkGenerator(object):
    """
    Factory responsible for creating units of work.

    This shall be run on the machine running OONI-cli. The returned WorkUnits
    can either be run locally or on a remote OONI Node or Network Node.
    """
    node = LocalNode
    size = 10

    def __init__(self, asset, test, arguments=None, start=None):
        self.assetGenerator = asset()
        self.Test = test
        self.arguments = arguments
        self.idx = 0
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
        # Plank asset
        p_asset = []
        for i in xrange(0, self.size):
            p_asset.append(self.assetGenerator.next())
        self.idx += 1
        return WorkUnit(self.node, p_asset, self.Test, self.idx, self.arguments)



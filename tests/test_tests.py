from twisted.internet import defer
from twisted.trial import unittest

from ooni.plugoo import work, tests

class TestsTestCase(unittest.TestCase):
    def setUp(self):
        class dummyReport:
            def __call__(self, *args, **kw):
                pass
        self.dummyreport = dummyReport()
        self.callbackResults = None
        self.errbackResults = None

    def _callback(self, *args, **kw):
        print "BBB"
        print args, kw
        print "CCCC"
        self.callbackResults = args, kw

    def _errback(self, *args, **kw):
        pass

    @defer.inlineCallbacks
    def test_fallThrough(self):
        """
        This tests to make sure that what is returned from the experiment
        method falls all the way through to control and finish.
        """
        test_dict = {"hello": "world"}
        class DummyTest(tests.OONITest):
            blocking = False
            def experiment(self, args):
                def cb(aaa):
                    return test_dict
                d = defer.Deferred()
                d.addCallback(cb)
                d.callback(None)
                return d

        test = DummyTest(None, None, self.dummyreport)
        yield test.startTest(None).addCallback(self._callback)
        self.assertEqual(self.callbackResults[0][0]['control'], test_dict)


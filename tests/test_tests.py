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
        #print args, kw
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
                def bla(a):
                    print a
                    return test_dict
                d2 = defer.Deferred()
                d2.addCallback(bla)
                from twisted.internet import reactor
                reactor.callLater(0.1, d2.callback, None)
                return d2

        test = DummyTest(None, None, self.dummyreport)
        yield test.startTest(None).addCallback(self._callback)
        self.assertEqual(self.callbackResults[0][0]['return_value'], test_dict)
        return


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
        self.callbackResults = args, kw

    def _errback(self, *args, **kw):
        pass

    def test_fallThrough(self):
        """
        This tests to make sure that what is returned from the experiment
        method falls all the way through to control and finish.
        """
        test_dict = {"hello": "world"}
        class DummyTest(tests.OONITest):
            def experiment(self, args):
                return test_dict

        test = DummyTest(None, None, self.dummyreport)
        test.startTest(None).addCallback(self._callback)
        self.assertEqual(self.callbackResults[0][0]['result'], test_dict)


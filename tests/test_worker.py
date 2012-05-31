from twisted.trial import unittest

from ooni.plugoo import work, tests

class WorkerTestCase(unittest.TestCase):
    def testWorkGenerator(self):
        class DummyTest:
            assets = {}
        dummytest = DummyTest()
        asset = []
        for i in range(10):
            asset.append(i)
        dummytest.assets['asset'] = asset
        wgen = work.WorkGenerator(dummytest)

        for j, x in enumerate(wgen):
            pass
        self.assertEqual(i, j)

    def testNoAssets(self):
        class DummyTest:
            assets = {'asset': None}
        dummytest = DummyTest()
        wgen = work.WorkGenerator(dummytest)
        i = 0
        for j in wgen:
            i += 1
        self.assertEqual(i, 1)


import os
from twisted.trial import unittest

from ooni.utils import pushFilenameStack
class TestUtils(unittest.TestCase):
    def test_pushFilenameStack(self):
        basefilename = os.path.join(os.getcwd(), 'dummyfile')
        f = open(basefilename, "w+")
        f.write("0\n")
        f.close()
        for i in xrange(1, 20):
            f = open(basefilename+".%s" % i, "w+")
            f.write("%s\n" % i)
            f.close()

        pushFilenameStack(basefilename)
        for i in xrange(1, 20):
            f = open(basefilename+".%s" % i)
            c = f.readlines()[0].strip()
            self.assertEqual(str(i-1), str(c))
            f.close()


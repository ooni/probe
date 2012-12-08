import unittest
from ooni.utils import pushFilenameStack

class TestUtils(unittest.TestCase):
    def test_pushFilenameStack(self):
        f = open("dummyfile", "w+")
        f.write("0\n")
        f.close()
        for i in xrange(1, 5):
            f = open("dummyfile.%s" % i, "w+")
            f.write("%s\n" % i)
            f.close()

        pushFilenameStack("dummyfile")
        for i in xrange(1, 5):
            f = open("dummyfile.%s" % i)
            c = f.readlines()[0].strip()
            self.assertEqual(str(i-1), str(c))
            f.close()


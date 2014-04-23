import os
from twisted.trial import unittest

from ooni.utils import pushFilenameStack, log


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

    def test_log_encode(self):
        logmsgs = (
            (r"spam\x07\x08", "spam\a\b"),
            (r"spam\x07\x08", u"spam\a\b"),
            (r"ham\u237e", u"ham"+u"\u237e")
        )
        for encoded_logmsg, logmsg in logmsgs:
            self.assertEqual(log.log_encode(logmsg), encoded_logmsg)

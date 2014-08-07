import os
from twisted.trial import unittest

from ooni.utils import pushFilenameStack, log, generate_filename


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_details = {
            'test_name': 'foo',
            'start_time': 1
        }
        self.extension = 'ext'
        self.prefix = 'prefix'
        self.basename = 'filename'
        self.filename = 'filename.txe'

    def test_pushFilenameStack(self):
        basefilename = os.path.join(os.getcwd(), 'dummyfile')
        f = open(basefilename, "w+")
        f.write("0\n")
        f.close()
        for i in xrange(1, 20):
            f = open("%s.%d" % (basefilename, i), "w+")
            f.write("%s\n" % i)
            f.close()

        pushFilenameStack(basefilename)
        for i in xrange(1, 20):
            f = open("%s.%d" % (basefilename, i))
            c = f.readlines()[0].strip()
            self.assertEqual(str(i-1), str(c))
            f.close()

        for i in xrange(1, 21):
            os.remove("%s.%d" % (basefilename, i))

    def test_log_encode(self):
        logmsgs = (
            (r"spam\x07\x08", "spam\a\b"),
            (r"spam\x07\x08", u"spam\a\b"),
            (r"ham\u237e", u"ham"+u"\u237e")
        )
        for encoded_logmsg, logmsg in logmsgs:
            self.assertEqual(log.log_encode(logmsg), encoded_logmsg)

    def test_generate_filename(self):
        filename = generate_filename(self.test_details)
        self.assertEqual(filename, 'foo-1970-01-01T000001Z')

    def test_generate_filename_with_extension(self):
        filename = generate_filename(self.test_details, extension=self.extension)
        self.assertEqual(filename, 'foo-1970-01-01T000001Z.ext')

    def test_generate_filename_with_prefix(self):
        filename = generate_filename(self.test_details, prefix=self.prefix)
        self.assertEqual(filename, 'prefix-foo-1970-01-01T000001Z')

    def test_generate_filename_with_extension_and_prefix(self):
        filename = generate_filename(self.test_details, prefix=self.prefix, extension=self.extension)
        self.assertEqual(filename, 'prefix-foo-1970-01-01T000001Z.ext')

    def test_generate_filename_with_filename(self):
        filename = generate_filename(self.test_details, filename=self.filename)
        self.assertEqual(filename, 'filename.txe')

    def test_generate_filename_with_extension_and_filename(self):
        filename = generate_filename(self.test_details, extension=self.extension, filename=self.filename)
        self.assertEqual(filename, 'filename.ext')

    def test_generate_filename_with_extension_and_basename(self):
        filename = generate_filename(self.test_details, extension=self.extension, filename=self.basename)
        self.assertEqual(filename, 'filename.ext')

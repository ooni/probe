import os
from twisted.trial import unittest

from ooni.utils import log, generate_filename, net


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.test_details = {
            'test_name': 'foo',
            'test_start_time': '2016-01-01 01:22:22'
        }
        self.extension = 'ext'
        self.prefix = 'prefix'
        self.basename = 'filename'
        self.filename = 'filename.txe'

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
        self.assertEqual(filename, 'foo-2016-01-01T012222Z')

    def test_generate_filename_with_extension(self):
        filename = generate_filename(self.test_details, extension=self.extension)
        self.assertEqual(filename, 'foo-2016-01-01T012222Z.ext')

    def test_generate_filename_with_prefix(self):
        filename = generate_filename(self.test_details, prefix=self.prefix)
        self.assertEqual(filename, 'prefix-foo-2016-01-01T012222Z')

    def test_generate_filename_with_extension_and_prefix(self):
        filename = generate_filename(self.test_details, prefix=self.prefix, extension=self.extension)
        self.assertEqual(filename, 'prefix-foo-2016-01-01T012222Z.ext')

    def test_get_addresses(self):
        addresses = net.getAddresses()
        assert isinstance(addresses, list)

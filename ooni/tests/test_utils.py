import os
import tempfile
from mock import patch

from twisted.trial import unittest

from ooni.utils import log, generate_filename, net
from ooni.utils.files import human_size_to_bytes, directory_usage


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
        self.assertEqual(filename, '20160101T012222Z-ZZ-AS0-foo')

    def test_generate_filename_with_extension(self):
        filename = generate_filename(self.test_details, extension=self.extension)
        self.assertEqual(filename, '20160101T012222Z-ZZ-AS0-foo.ext')

    def test_generate_filename_with_prefix(self):
        filename = generate_filename(self.test_details, prefix=self.prefix)
        self.assertEqual(filename, 'prefix-20160101T012222Z-ZZ-AS0-foo')

    def test_generate_filename_with_extension_and_prefix(self):
        filename = generate_filename(self.test_details, prefix=self.prefix, extension=self.extension)
        self.assertEqual(filename, 'prefix-20160101T012222Z-ZZ-AS0-foo.ext')

    def test_get_addresses(self):
        addresses = net.getAddresses()
        assert isinstance(addresses, list)

    def test_human_size(self):
        self.assertEqual(
            human_size_to_bytes("1G"),
            1024**3
        )
        self.assertEqual(
            human_size_to_bytes("1.3M"),
            1.3 * 1024**2
        )
        self.assertEqual(
            human_size_to_bytes("1.2K"),
            1.2 * 1024
        )
        self.assertEqual(
            human_size_to_bytes("1"),
            1.0
        )
        self.assertEqual(
            human_size_to_bytes("100.2"),
            100.2
        )

    def test_directory_usage(self):
        tmp_dir = tempfile.mkdtemp()
        with open(os.path.join(tmp_dir, "something.txt"), "w") as out_file:
            out_file.write("A"*1000)
        os.mkdir(os.path.join(tmp_dir, "subdir"))
        with open(os.path.join(tmp_dir, "subdir", "something.txt"), "w") as out_file:
            out_file.write("A"*1000)
        self.assertEqual(directory_usage(tmp_dir), 1000*2)

class LoggingTests(unittest.TestCase):
    def setUp(self):
        self.dir = self.mktemp()
        os.makedirs(self.dir)
        self.name = "test.log"
        self.path = os.path.join(self.dir, self.name)

    @patch('ooni.settings.config')
    def test_length_rotate(self, mock_config):
        mock_config.basic.loglevel = 'DEBUG'
        mock_config.advanced.debug = False
        mock_config.basic.rotate = 'length'
        mock_config.basic.rotate_length = '1M'

        ooni_logger = log.OONILogger()
        ooni_logger.start(logfile=self.path)

        ooni_logger.debug("1"*(1024**2))

        # This will trigger the rotation
        ooni_logger.debug("2")

        ooni_logger.stop()
        self.assertTrue(os.path.exists("{0}.1".format(self.path)))
        self.assertFalse(os.path.exists("{0}.2".format(self.path)))


    @patch('ooni.settings.config')
    def test_log_levels(self, mock_config):
        mock_config.basic.loglevel = 'WARN'
        mock_config.advanced.debug = False
        mock_config.basic.rotate = None

        ooni_logger = log.OONILogger()
        ooni_logger.start(logfile=self.path)
        ooni_logger.msg("Should not print")
        ooni_logger.warn("Will print")
        ooni_logger.err("Will print")
        ooni_logger.debug("Should not print")
        ooni_logger.stop()
        with open(self.path) as in_file:
            self.assertEqual(
                len(in_file.readlines()),
                2
            )

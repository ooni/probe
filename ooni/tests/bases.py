from twisted.trial import unittest

from ooni.settings import config


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        config.initialize_ooni_home("ooni_home")

    def skipTest(self, reason):
        raise unittest.SkipTest(reason)

    def tearDown(self):
        config.set_paths()
        config.read_config_file()

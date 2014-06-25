from twisted.trial import unittest

from ooni.settings import config


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        config.initialize_ooni_home("ooni_home")

    def tearDown(self):
        config.read_config_file()
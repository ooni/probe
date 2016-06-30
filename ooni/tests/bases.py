import shutil

from twisted.trial import unittest

from ooni.settings import config


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.config = config
        self.config.initialize_ooni_home("ooni_home")

    def skipTest(self, reason):
        raise unittest.SkipTest(reason)

    def tearDown(self):
        self.config.set_paths()
        self.config.read_config_file()
        shutil.rmtree(self.config.ooni_home)

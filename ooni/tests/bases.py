import os
import shutil

from twisted.trial import unittest

from ooni.settings import config


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.ooni_home_dir = os.path.abspath("ooni_home")
        self.config = config
        self.config.initialize_ooni_home(self.ooni_home_dir)
        config.is_initialized = lambda: True
        super(ConfigTestCase, self).setUp()

    def skipTest(self, reason):
        raise unittest.SkipTest(reason)

    def tearDown(self):
        shutil.rmtree("ooni_home")

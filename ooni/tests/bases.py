import os

from twisted.trial import unittest

from ooni.settings import config


class ConfigTestCase(unittest.TestCase):
    def setUp(self):
        config.global_options['datadir'] = os.path.join(__file__, '..', '..', '..', 'data')
        config.global_options['datadir'] = os.path.abspath(config.global_options['datadir'])
        config.initialize_ooni_home("ooni_home")

    def tearDown(self):
        config.read_config_file()

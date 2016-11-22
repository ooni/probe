import os

from StringIO import StringIO
from copy import deepcopy

import yaml

from mock import patch

from twisted.internet import defer
from twisted.trial import unittest

from hashlib import sha256
from ooni import errors
from ooni.deck.store import input_store
from ooni.deck.backend import lookup_collector_and_test_helpers
from ooni.deck.deck import nettest_to_path, NGDeck, options_to_args
from ooni.deck.legacy import convert_legacy_deck
from ooni.tests.bases import ConfigTestCase
from ooni.tests.mocks import MockBouncerClient, MockCollectorClient

FAKE_BOUNCER_ADDRESS = "httpo://thirteenchars123.onion"

net_test_string = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', None, 'ham']]

class DummyTestCase(NetTestCase):

    usageOptions = UsageOptions
    requiredTestHelpers = {'spam': 'test-helper-typeA'}

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'
"""


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.filename = ""
        self.cwd = os.getcwd()
        self.dummy_deck_content = """- options:
            collector: null
            annotations: null
            help: 0
            logfile: null
            no-default-reporter: 0
            parallelism: null
            pcapfile: null
            reportfile: null
            resume: 0
            subargs: []
            test_file: manipulation/http_invalid_request_line
            testdeck: null
"""
        self.dummy_deck_content_with_many_tests = """- options:
            collector: null
            help: 0
            logfile: null
            no-default-reporter: 0
            parallelism: null
            pcapfile: null
            reportfile: null
            resume: 0
            subargs: [-b, "1.1.1.1"]
            test_file: manipulation/http_invalid_request_line
            testdeck: null
- options:
            collector: null
            help: 0
            logfile: null
            no-default-reporter: 0
            parallelism: null
            pcapfile: null
            reportfile: null
            resume: 0
            subargs: [-b, "2.2.2.2"]
            test_file: manipulation/http_invalid_request_line
            testdeck: null
"""
        super(BaseTestCase, self).setUp()

class TestDeck(BaseTestCase, ConfigTestCase):
    def setUp(self):
        super(TestDeck, self).setUp()
        deck_hash = sha256(self.dummy_deck_content).hexdigest()
        self.deck_file = os.path.join(self.cwd, deck_hash)
        with open(self.deck_file, 'w+') as f:
            f.write(self.dummy_deck_content)
        with open(os.path.join(self.cwd, 'dummy_test.py'), 'w+') as f:
            f.write(net_test_string)

    def tearDown(self):
        os.remove(os.path.join(self.cwd, 'dummy_test.py'))
        os.remove(self.deck_file)
        if self.filename != "":
            os.remove(self.filename)
        super(TestDeck, self).tearDown()

    def test_open_deck(self):
        deck = NGDeck()
        deck.open(self.deck_file)
        assert len(deck.tasks) == 1

    def test_load_deck_with_global_options(self):
        global_options = {
            "annotations": {"spam": "ham"},
            "collector": "httpo://thirteenchars123.onion"
        }
        deck = NGDeck(global_options=global_options)
        deck.open(self.deck_file)
        self.assertEqual(
            deck.tasks[0].ooni['net_test_loader'].annotations,
            global_options['annotations']
        )
        self.assertEqual(
            deck.tasks[0].ooni['net_test_loader'].collector.base_address,
            global_options['collector'].replace("httpo://", "http://")
        )

    @patch('ooni.deck.deck.BouncerClient', MockBouncerClient)
    @patch('ooni.deck.deck.CollectorClient', MockCollectorClient)
    @patch('ooni.deck.backend.CollectorClient', MockCollectorClient)
    @defer.inlineCallbacks
    def test_lookup_test_helpers_and_collector(self):
        deck = NGDeck()
        deck.open(self.deck_file)

        self.assertEqual(
            len(deck.tasks[0].ooni['net_test_loader'].missingTestHelpers),
            1
        )

        yield lookup_collector_and_test_helpers(
            net_test_loaders=[deck.tasks[0].ooni['net_test_loader']],
            preferred_backend='onion',
            bouncer=MockBouncerClient()
        )

        self.assertEqual(
            deck.tasks[0].ooni['net_test_loader'].collector.settings['address'],
            'httpo://thirteenchars123.onion'
        )

        self.assertEqual(
            deck.tasks[0].ooni['net_test_loader'].localOptions['backend'],
            '127.0.0.1'
        )


    def test_deck_with_many_tests(self):
        os.remove(self.deck_file)
        deck_hash = sha256(self.dummy_deck_content_with_many_tests).hexdigest()
        self.deck_file = os.path.join(self.cwd, deck_hash)
        with open(self.deck_file, 'w+') as f:
            f.write(self.dummy_deck_content_with_many_tests)
        deck = NGDeck()
        deck.open(self.deck_file)

        self.assertEqual(
            deck.tasks[0].ooni['net_test_loader'].localOptions['backend'],
            '1.1.1.1'
        )
        self.assertEqual(
            deck.tasks[1].ooni['net_test_loader'].localOptions['backend'],
            '2.2.2.2'
        )

    def test_nettest_to_path(self):
        path_a = nettest_to_path("blocking/http_requests")
        path_b = nettest_to_path("http_requests")
        self.assertEqual(path_a, path_b)
        self.assertRaises(errors.NetTestNotFound,
                          nettest_to_path,
                          "invalid_test")

    @patch('ooni.deck.deck.BouncerClient', MockBouncerClient)
    @patch('ooni.deck.deck.CollectorClient', MockCollectorClient)
    @patch('ooni.deck.backend.CollectorClient', MockCollectorClient)
    @defer.inlineCallbacks
    def test_lookup_test_helpers_and_collector_cloudfront(self):
        self.config.advanced.preferred_backend = "cloudfront"
        deck = NGDeck()
        deck.open(self.deck_file)
        first_net_test_loader = deck.tasks[0].ooni['net_test_loader']
        net_test_loaders = map(lambda task: task.ooni['net_test_loader'],
                               deck.tasks)
        self.assertEqual(len(first_net_test_loader.missingTestHelpers), 1)

        yield lookup_collector_and_test_helpers(
            net_test_loaders=net_test_loaders ,
            preferred_backend='cloudfront',
            bouncer=MockBouncerClient()
        )

        self.assertEqual(
            first_net_test_loader.collector.settings['address'],
            'https://address.cloudfront.net'
        )
        self.assertEqual(
            first_net_test_loader.collector.settings['front'],
            'front.cloudfront.net'
        )

        self.assertEqual(
            first_net_test_loader.localOptions['backend'],
            '127.0.0.1'
        )

    @patch('ooni.deck.deck.BouncerClient', MockBouncerClient)
    @patch('ooni.deck.deck.CollectorClient', MockCollectorClient)
    @patch('ooni.deck.backend.CollectorClient', MockCollectorClient)
    @defer.inlineCallbacks
    def test_lookup_test_helpers_and_collector_https(self):
        self.config.advanced.preferred_backend = "https"
        deck = NGDeck()
        deck.open(self.deck_file)

        first_net_test_loader = deck.tasks[0].ooni['net_test_loader']
        net_test_loaders = map(lambda task: task.ooni['net_test_loader'],
                               deck.tasks)

        self.assertEqual(len(first_net_test_loader .missingTestHelpers), 1)

        yield lookup_collector_and_test_helpers(
            net_test_loaders=net_test_loaders,
            preferred_backend='https',
            bouncer=MockBouncerClient()
        )

        self.assertEqual(
            first_net_test_loader.collector.settings['address'],
            'https://collector.ooni.io'
        )

        self.assertEqual(
            first_net_test_loader.localOptions['backend'],
            '127.0.0.1'
        )

class TestInputStore(ConfigTestCase):
    @defer.inlineCallbacks
    def test_update_input_store(self):
        self.skipTest("antani")
        yield input_store.update("ZZ")
        print os.listdir(os.path.join(
            self.config.resources_directory, "citizenlab-test-lists"))
        print os.listdir(os.path.join(self.config.inputs_directory))

TASK_DATA = {
    "name": "Some Task",
    "ooni": {
        "test_name": "web_connectivity",
        "file": "$citizen_lab_global_urls"
    }
}

DECK_DATA = {
    "name": "My deck",
    "description": "Something",
    "tasks": [
        deepcopy(TASK_DATA)
    ]
}

LEGACY_DECK = """
- options:
    annotations: null
    bouncer: null
    collector: null
    no-collector: 0
    no-geoip: 0
    no-yamloo: 0
    reportfile: null
    subargs: [--flag, --key, value]
    test_file: manipulation/http_invalid_request_line
    verbose: 0
- options:
    annotations: null
    bouncer: null
    collector: null
    no-collector: 0
    no-geoip: 0
    no-yamloo: 0
    reportfile: null
    subargs: []
    test_file: manipulation/http_header_field_manipulation
    verbose: 0
- options:
    annotations: null
    bouncer: null
    collector: null
    no-collector: 0
    no-geoip: 0
    no-yamloo: 0
    reportfile: null
    subargs: [-f, /path/to/citizenlab-urls-global.txt]
    test_file: blocking/web_connectivity
    verbose: 0
"""

class TestNGDeck(ConfigTestCase):
    def test_deck_task(self):
        #yield input_store.update("ZZ")
        #deck_task = DeckTask(TASK_DATA)
        #self.assertIsInstance(deck_task.ooni["net_test_loader"],
        #                      NetTestLoader)
        pass

    def test_deck_load(self):
        #yield input_store.update("ZZ")
        #deck = NGDeck(deck_data=DECK_DATA)
        #self.assertEqual(len(deck.tasks), 1)
        pass

    def test_convert_legacy_deck(self):
        legacy_deck = yaml.safe_load(StringIO(LEGACY_DECK))
        ng_deck = convert_legacy_deck(legacy_deck)
        self.assertEqual(len(ng_deck['tasks']), 3)
        task_names = map(lambda task: task['ooni']['test_name'],
                         ng_deck['tasks'])
        self.assertItemsEqual(task_names, [
            "manipulation/http_invalid_request_line",
            "manipulation/http_header_field_manipulation",
            "blocking/web_connectivity"
        ])
        tasks = map(lambda task: task['ooni'], ng_deck['tasks'])
        self.assertEqual(
            tasks[2]['f'],
            '/path/to/citizenlab-urls-global.txt')

    def test_options_to_args(self):
        args = options_to_args({"f": "foobar.txt", "bar": None, "help": 0})
        print(args)

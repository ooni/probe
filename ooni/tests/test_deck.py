import os

from twisted.internet import defer
from twisted.trial import unittest

from hashlib import sha256
from ooni import errors
from ooni.deck import InputFile, Deck, nettest_to_path
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


class TestInputFile(BaseTestCase):
    def tearDown(self):
        if self.filename != "":
            os.remove(self.filename)

    def test_file_cached(self):
        self.filename = file_hash = sha256(self.dummy_deck_content).hexdigest()
        input_file = InputFile(file_hash, base_path='.')
        with open(file_hash, 'w+') as f:
            f.write(self.dummy_deck_content)
        assert input_file.fileCached

    def test_file_invalid_hash(self):
        self.filename = invalid_hash = 'a' * 64
        with open(invalid_hash, 'w+') as f:
            f.write("b" * 100)
        input_file = InputFile(invalid_hash, base_path='.')
        self.assertRaises(AssertionError, input_file.verify)

    def test_save_descriptor(self):
        descriptor = {
            'name': 'spam',
            'id': 'spam',
            'version': 'spam',
            'author': 'spam',
            'date': 'spam',
            'description': 'spam'
        }
        file_id = 'a' * 64
        self.filename = file_id + '.desc'
        input_file = InputFile(file_id, base_path='.')
        input_file.load(descriptor)
        input_file.save()
        assert os.path.isfile(self.filename)

        assert input_file.descriptorCached


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
        deck = Deck(bouncer=FAKE_BOUNCER_ADDRESS,
                    decks_directory=".")
        deck.loadDeck(self.deck_file)
        assert len(deck.netTestLoaders) == 1

    def test_load_deck_with_global_options(self):
        global_options = {
            "annotations": {"spam": "ham"},
            "collector": "httpo://thirteenchars123.onion"
        }
        deck = Deck(bouncer=FAKE_BOUNCER_ADDRESS,
                    decks_directory=".")
        deck.loadDeck(self.deck_file,
                      global_options=global_options)
        self.assertEqual(
            deck.netTestLoaders[0].annotations,
            global_options['annotations']
        )
        self.assertEqual(
            deck.netTestLoaders[0].collector.base_address,
            global_options['collector'].replace("httpo://", "http://")
        )

    def test_save_deck_descriptor(self):
        deck = Deck(bouncer=FAKE_BOUNCER_ADDRESS,
                    decks_directory=".")
        deck.loadDeck(self.deck_file)
        deck.load({'name': 'spam',
                   'id': 'spam',
                   'version': 'spam',
                   'author': 'spam',
                   'date': 'spam',
                   'description': 'spam'
                   })
        deck.save()
        self.filename = self.deck_file + ".desc"
        deck.verify()

    @defer.inlineCallbacks
    def test_lookup_test_helpers_and_collector(self):
        deck = Deck(bouncer=FAKE_BOUNCER_ADDRESS,
                    decks_directory=".")
        deck.bouncer = MockBouncerClient(FAKE_BOUNCER_ADDRESS)
        deck._BouncerClient = MockBouncerClient
        deck._CollectorClient = MockCollectorClient
        deck.loadDeck(self.deck_file)

        self.assertEqual(len(deck.netTestLoaders[0].missingTestHelpers), 1)

        yield deck.lookupCollectorAndTestHelpers()

        self.assertEqual(deck.netTestLoaders[0].collector.settings['address'],
                         'httpo://thirteenchars123.onion')

        self.assertEqual(deck.netTestLoaders[0].localOptions['backend'],
                         '127.0.0.1')


    def test_deck_with_many_tests(self):
        os.remove(self.deck_file)
        deck_hash = sha256(self.dummy_deck_content_with_many_tests).hexdigest()
        self.deck_file = os.path.join(self.cwd, deck_hash)
        with open(self.deck_file, 'w+') as f:
            f.write(self.dummy_deck_content_with_many_tests)
        deck = Deck(decks_directory=".")
        deck.loadDeck(self.deck_file)

        self.assertEqual(
            deck.netTestLoaders[0].localOptions['backend'],
            '1.1.1.1'
        )
        self.assertEqual(
            deck.netTestLoaders[1].localOptions['backend'],
            '2.2.2.2'
        )

    def test_nettest_to_path(self):
        path_a = nettest_to_path("blocking/http_requests")
        path_b = nettest_to_path("http_requests")
        self.assertEqual(path_a, path_b)
        self.assertRaises(errors.NetTestNotFound,
                          nettest_to_path,
                          "invalid_test")

    @defer.inlineCallbacks
    def test_lookup_test_helpers_and_collector_cloudfront(self):
        self.config.advanced.preferred_backend = "cloudfront"
        deck = Deck(bouncer=FAKE_BOUNCER_ADDRESS,
                    decks_directory=".")
        deck.bouncer = MockBouncerClient(FAKE_BOUNCER_ADDRESS)
        deck._BouncerClient = MockBouncerClient
        deck._CollectorClient = MockCollectorClient
        deck.loadDeck(self.deck_file)

        self.assertEqual(len(deck.netTestLoaders[0].missingTestHelpers), 1)

        yield deck.lookupCollectorAndTestHelpers()

        self.assertEqual(
            deck.netTestLoaders[0].collector.settings['address'],
            'https://address.cloudfront.net'
        )
        self.assertEqual(
            deck.netTestLoaders[0].collector.settings['front'],
            'front.cloudfront.net'
        )

        self.assertEqual(
            deck.netTestLoaders[0].localOptions['backend'],
            '127.0.0.1'
        )


    @defer.inlineCallbacks
    def test_lookup_test_helpers_and_collector_https(self):
        self.config.advanced.preferred_backend = "https"
        deck = Deck(bouncer=FAKE_BOUNCER_ADDRESS,
                    decks_directory=".")
        deck.bouncer = MockBouncerClient(FAKE_BOUNCER_ADDRESS)
        deck._BouncerClient = MockBouncerClient
        deck._CollectorClient = MockCollectorClient
        deck.loadDeck(self.deck_file)

        self.assertEqual(len(deck.netTestLoaders[0].missingTestHelpers), 1)

        yield deck.lookupCollectorAndTestHelpers()

        self.assertEqual(
            deck.netTestLoaders[0].collector.settings['address'],
            'https://collector.ooni.io'
        )

        self.assertEqual(
            deck.netTestLoaders[0].localOptions['backend'],
            '127.0.0.1'
        )

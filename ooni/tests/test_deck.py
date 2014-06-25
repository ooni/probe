import os

from twisted.internet import defer
from twisted.trial import unittest

from hashlib import sha256
from ooni.deck import InputFile, Deck
from ooni.tests.mocks import MockOONIBClient

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


class TestDeck(BaseTestCase):
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

    def test_open_deck(self):
        deck = Deck(decks_directory=".")
        deck.bouncer = "httpo://foo.onion"
        deck.loadDeck(self.deck_file)
        assert len(deck.netTestLoaders) == 1

    def test_save_deck_descriptor(self):
        deck = Deck(decks_directory=".")
        deck.bouncer = "httpo://foo.onion"
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
    def test_lookuptest_helpers(self):
        deck = Deck(decks_directory=".")
        deck.bouncer = "httpo://foo.onion"
        deck.oonibclient = MockOONIBClient()
        deck.loadDeck(self.deck_file)
        yield deck.lookupTestHelpers()

        assert deck.netTestLoaders[0].collector == 'httpo://thirteenchars1234.onion'

        required_test_helpers = deck.netTestLoaders[0].requiredTestHelpers
        assert len(required_test_helpers) == 1
        assert required_test_helpers[0]['test_class'].localOptions['backend'] == '127.0.0.1'

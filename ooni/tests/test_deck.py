import os

from twisted.internet import defer
from twisted.trial import unittest

from hashlib import sha256
from ooni.deck import InputFile, Deck

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
            test_file: %s/dummy_test.py
            testdeck: null
""" % self.cwd

class TestInputFile(BaseTestCase):
    def test_file_cached(self):
        file_hash = sha256(self.dummy_deck_content).hexdigest()
        input_file = InputFile(file_hash, base_path='.')
        with open(file_hash, 'w+') as f:
            f.write(self.dummy_deck_content)
        assert input_file.fileCached

    def test_file_invalid_hash(self):
        invalid_hash = 'a'*64
        with open(invalid_hash, 'w+') as f:
            f.write("b"*100)
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
        file_id = 'a'*64
        input_file = InputFile(file_id, base_path='.')
        input_file.load(descriptor)
        input_file.save()
        assert os.path.isfile(file_id)

        assert input_file.descriptorCached

class MockOONIBClient(object):
    def lookupTestHelpers(self, required_test_helpers):
        ret = {
            'default': {
                'address': '127.0.0.1',
                'collector': 'httpo://thirteenchars1234.onion'
            }
        }
        for required_test_helper in required_test_helpers:
            ret[required_test_helper] = {
                    'address': '127.0.0.1',
                    'collector': 'httpo://thirteenchars1234.onion'
        }
        return defer.succeed(ret)

class TestDeck(BaseTestCase):
    def setUp(self):
        super(TestDeck, self).setUp()
        deck_hash = sha256(self.dummy_deck_content).hexdigest()
        self.deck_file = os.path.join(self.cwd, deck_hash)
        with open(self.deck_file, 'w+') as f:
            f.write(self.dummy_deck_content)
        with open(os.path.join(self.cwd, 'dummy_test.py'), 'w+') as f:
            f.write(net_test_string)

    def test_open_deck(self):
        deck = Deck(deckFile=self.deck_file, decks_directory=".")
        assert len(deck.netTestLoaders) == 1

    def test_save_deck_descriptor(self):
        deck = Deck(deckFile=self.deck_file, decks_directory=".")
        deck.load({'name': 'spam',
            'id': 'spam',
            'version': 'spam',
            'author': 'spam',
            'date': 'spam',
            'description': 'spam'
        })
        deck.save()
        deck.verify()
    
    @defer.inlineCallbacks
    def test_lookuptest_helpers(self):
        deck = Deck(deckFile=self.deck_file, decks_directory=".")
        deck.oonibclient = MockOONIBClient()
        yield deck.lookupTestHelpers()

        assert deck.netTestLoaders[0].collector == 'httpo://thirteenchars1234.onion'

        required_test_helpers = deck.netTestLoaders[0].requiredTestHelpers
        assert len(required_test_helpers) == 1
        assert required_test_helpers[0]['test_class'].localOptions['spam'] == '127.0.0.1'


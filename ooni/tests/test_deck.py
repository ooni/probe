import os

from twisted.trial import unittest

from hashlib import sha256
from ooni.deck import InputFile

dummy_deck_content = """- options:
    collector: null
    help: 0
    logfile: null
    no-default-reporter: 0
    parallelism: null
    pcapfile: null
    reportfile: null
    resume: 0
    subargs: []
    test_file: some_dummy_test
    testdeck: null
"""

class TestInputFile(unittest.TestCase):
    def test_file_cached(self):
        file_hash = sha256(dummy_deck_content).hexdigest()
        input_file = InputFile(file_hash, base_path='.')
        with open(file_hash, 'w+') as f:
            f.write(dummy_deck_content)
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

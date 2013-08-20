from twisted.trial import unittest
from twisted.internet import defer

from ooni.oonibclient import OONIBClient

input_id = 'e0611ecd28bead38a7afeb4dda8ae3449d0fc2e1ba53fa7355f2799dce9af290'

class TestOONIBClient(unittest.TestCase):
    def setUp(self):
        self.oonibclient = OONIBClient('http://127.0.0.1:8888')
    
    @defer.inlineCallbacks
    def test_query(self):
        res = yield self.oonibclient.queryBackend('GET', '/policy/input')
        self.assertTrue(isinstance(res, list))
    
    def test_get_input_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(inputList, list))

    def test_get_input_descriptor(self):
        input_descriptor = yield self.oonibclient.getInput(input_id)
        for key in ['name', 'description', 
                    'version', 'author', 'date']:
            self.assertTrue(key in input_descriptor.keys())

    def test_download_input(self):
        pass

    def test_get_deck_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(inputList, list))

    def test_get_deck_descriptor(self):
        pass

    def test_download_deck(self):
        pass

    def test_get_nettest_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(inputList, list))

    def test_get_nettest_descriptor(self):
        pass

    def test_download_nettest(self):
        pass

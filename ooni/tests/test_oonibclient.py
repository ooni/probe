from twisted.trial import unittest
from twisted.internet import defer

from ooni.oonibclient import OONIBClient

input_id = '37e60e13536f6afe47a830bfb6b371b5cf65da66d7ad65137344679b24fdccd1'

class TestOONIBClient(unittest.TestCase):
    def setUp(self):
        self.oonibclient = OONIBClient('http://127.0.0.1:8888')
    
    @defer.inlineCallbacks
    def test_query(self):
        res = yield self.oonibclient.queryBackend('GET', '/policy/input')
        self.assertTrue(isinstance(res, list))
    
    @defer.inlineCallbacks
    def test_get_input_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(input_list, list))

    @defer.inlineCallbacks
    def test_get_input_descriptor(self):
        input_descriptor = yield self.oonibclient.getInput(input_id)
        for key in ['name', 'description', 
                    'version', 'author', 'date']:
            self.assertTrue(key in input_descriptor.keys())

    @defer.inlineCallbacks
    def test_download_input(self):
        yield self.oonibclient.downloadInput(input_id, input_id)

    @defer.inlineCallbacks
    def test_get_deck_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(input_list, list))

    def test_get_deck_descriptor(self):
        pass

    def test_download_deck(self):
        pass

    @defer.inlineCallbacks
    def test_get_nettest_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(input_list, list))

    def test_get_nettest_descriptor(self):
        pass

    def test_download_nettest(self):
        pass

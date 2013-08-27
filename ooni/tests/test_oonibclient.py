import os
import shutil
import socket

from twisted.trial import unittest
from twisted.internet import defer

from ooni import errors as e
from ooni.utils import log
from ooni.settings import config
from ooni.oonibclient import OONIBClient

data_dir = '/tmp/testooni'
config.advanced.data_dir = data_dir
input_id = '37e60e13536f6afe47a830bfb6b371b5cf65da66d7ad65137344679b24fdccd1'

class TestOONIBClient(unittest.TestCase):
    def setUp(self):
        host = '127.0.0.1'
        port = 8888
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.shutdown(2)
            try: shutil.rmtree(data_dir)
            except: pass
            os.mkdir(data_dir)
            os.mkdir(os.path.join(data_dir, 'inputs'))
        except Exception as ex:
            self.skipTest("OONIB must be listening on port 8888 to run this test (tor_hidden_service: false)")
        self.oonibclient = OONIBClient('http://' + host + ':' + str(port))
    
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
                    'version', 'author', 'date', 'id']:
            self.assertTrue(hasattr(input_descriptor, key))

    @defer.inlineCallbacks
    def test_download_input(self):
        yield self.oonibclient.downloadInput(input_id)

    @defer.inlineCallbacks
    def test_get_deck_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(input_list, list))

    def test_get_deck_descriptor(self):
        pass

    def test_download_deck(self):
        pass

    def test_lookup_invalid_helpers(self):
        return self.failUnlessFailure(
                self.oonibclient.lookupTestHelpers(
                    ['dns', 'http-return-json-headers', 'sdadsadsa']
                ), e.CouldNotFindTestHelper)

    @defer.inlineCallbacks
    def test_lookup_test_helpers(self):
        helpers = yield self.oonibclient.lookupTestHelpers(['dns', 'http-return-json-headers'])
        self.assertTrue(len(helpers) == 1)

    @defer.inlineCallbacks
    def test_get_nettest_list(self):
        input_list = yield self.oonibclient.getInputList()
        self.assertTrue(isinstance(input_list, list))

    def test_get_nettest_descriptor(self):
        pass

    def test_download_nettest(self):
        pass

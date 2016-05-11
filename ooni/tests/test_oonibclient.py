import os
import shutil
import socket

from twisted.internet import defer
from twisted.web import error

from ooni import errors as e
from ooni.settings import config
from ooni.backend_client import CollectorClient, BouncerClient
from ooni.tests.bases import ConfigTestCase

input_id = '37e60e13536f6afe47a830bfb6b371b5cf65da66d7ad65137344679b24fdccd1'
deck_id = 'd4ae40ecfb3c1b943748cce503ab8233efce7823f3e391058fc0f87829c644ed'


class TestOONIBClient(ConfigTestCase):
    def setUp(self):
        super(TestOONIBClient, self).setUp()
        host = '127.0.0.1'
        port = 8889
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            s.shutdown(2)

            data_dir = '/tmp/testooni'
            config.advanced.data_dir = data_dir

            if os.path.exists(data_dir):
                shutil.rmtree(data_dir)
            os.mkdir(data_dir)
            os.mkdir(os.path.join(data_dir, 'inputs'))
            os.mkdir(os.path.join(data_dir, 'decks'))
        except Exception:
            self.skipTest("OONIB must be listening on port 8888 to run this test (tor_hidden_service: false)")
        self.collector_client = CollectorClient('http://' + host + ':' + str(port))

    @defer.inlineCallbacks
    def test_query(self):
        res = yield self.collector_client.queryBackend('GET', '/policy/input')
        self.assertTrue(isinstance(res, list))

    @defer.inlineCallbacks
    def test_get_input_list(self):
        input_list = yield self.collector_client.getInputList()
        self.assertTrue(isinstance(input_list, list))

    @defer.inlineCallbacks
    def test_get_input_descriptor(self):
        input_descriptor = yield self.collector_client.getInput(input_id)
        for key in ['name', 'description',
                    'version', 'author', 'date', 'id']:
            self.assertTrue(hasattr(input_descriptor, key))

    @defer.inlineCallbacks
    def test_download_input(self):
        yield self.collector_client.downloadInput(input_id)

    @defer.inlineCallbacks
    def test_get_deck_list(self):
        deck_list = yield self.collector_client.getDeckList()
        self.assertTrue(isinstance(deck_list, list))

    @defer.inlineCallbacks
    def test_get_deck_descriptor(self):
        deck_descriptor = yield self.collector_client.getDeck(deck_id)
        for key in ['name', 'description',
                    'version', 'author', 'date', 'id']:
            self.assertTrue(hasattr(deck_descriptor, key))

    @defer.inlineCallbacks
    def test_download_deck(self):
        yield self.collector_client.downloadDeck(deck_id)

    def test_lookup_invalid_helpers(self):
        bouncer_client = BouncerClient('http://127.0.0.1:8888')
        return self.failUnlessFailure(
            bouncer_client.lookupTestHelpers([
                'sdadsadsa', 'dns'
            ]), e.CouldNotFindTestHelper)

    @defer.inlineCallbacks
    def test_lookup_no_test_helpers(self):
        bouncer_client = BouncerClient('http://127.0.0.1:8888')
        required_helpers = []
        helpers = yield bouncer_client.lookupTestHelpers(required_helpers)
        self.assertTrue('default' in helpers.keys())

    @defer.inlineCallbacks
    def test_lookup_test_helpers(self):
        bouncer_client = BouncerClient('http://127.0.0.1:8888')
        required_helpers = [u'http-return-json-headers', u'dns']
        helpers = yield bouncer_client.lookupTestHelpers(required_helpers)
        self.assertEqual(set(helpers.keys()), set(required_helpers + [u'default']))
        self.assertTrue(helpers['http-return-json-headers']['address'].startswith('http'))
        self.assertTrue(int(helpers['dns']['address'].split('.')[0]))

    @defer.inlineCallbacks
    def test_input_descriptor_not_found(self):
        yield self.assertFailure(self.collector_client.queryBackend('GET',
                                                             '/input/' + 'a'*64), e.OONIBInputDescriptorNotFound)

    @defer.inlineCallbacks
    def test_http_errors(self):
        yield self.assertFailure(self.collector_client.queryBackend('PUT',
                                                     '/policy/input'), error.Error)

    @defer.inlineCallbacks
    def test_create_report(self):
        res = yield self.collector_client.queryBackend('POST', '/report', {
            'software_name': 'spam',
            'software_version': '2.0',
            'probe_asn': 'AS0',
            'probe_cc': 'ZZ',
            'test_name': 'foobar',
            'test_version': '1.0',
            'input_hashes': []
        })
        assert isinstance(res['report_id'], unicode)

    @defer.inlineCallbacks
    def test_report_lifecycle(self):
        res = yield self.collector_client.queryBackend('POST', '/report', {
            'software_name': 'spam',
            'software_version': '2.0',
            'probe_asn': 'AS0',
            'probe_cc': 'ZZ',
            'test_name': 'foobar',
            'test_version': '1.0',
            'input_hashes': []
        })
        report_id = str(res['report_id'])

        res = yield self.collector_client.queryBackend('POST', '/report/' + report_id, {
            'content': '---\nspam: ham\n...\n'
        })

        res = yield self.collector_client.queryBackend('POST', '/report/' + report_id, {
            'content': '---\nspam: ham\n...\n'
        })

        res = yield self.collector_client.queryBackend('POST', '/report/' + report_id +
                                        '/close')

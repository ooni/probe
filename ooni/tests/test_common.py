import json
from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.web.client import readBody

from . import is_internet_connected

from ooni.common.http_utils import representBody
from ooni.common.ip_utils import is_public_ipv4_address, is_private_ipv4_address
from ooni.common.txextra import FixedRedirectAgent, TrueHeadersAgent, TrueHeaders

class TestHTTPUtils(unittest.TestCase):
    def test_represent_body(self):
        self.assertEqual(representBody(None), None)
        self.assertEqual(representBody("spam\xcf\x83"), u'spam\u03c3')
        self.assertEqual(representBody("\xff\x00"),
                         {'data': '/wA=', 'format': 'base64'})

class TestIPUtils(unittest.TestCase):
    def test_is_public_ipv4(self):
        self.assertTrue(is_public_ipv4_address('8.8.8.8'))
        self.assertFalse(is_public_ipv4_address('example.com'))
        self.assertFalse(is_public_ipv4_address('127.0.0.1'))
        self.assertFalse(is_public_ipv4_address('192.168.1.1'))

    def test_is_private_ipv4(self):
        self.assertFalse(is_private_ipv4_address('8.8.8.8'))
        self.assertFalse(is_private_ipv4_address('example.com'))
        self.assertTrue(is_private_ipv4_address('127.0.0.1'))
        self.assertTrue(is_private_ipv4_address('192.168.2.2'))

class TestTxExtra(unittest.TestCase):
    @defer.inlineCallbacks
    def test_redirect_works(self):
        if not is_internet_connected():
            raise unittest.SkipTest("Internet connection missing")

        agent = FixedRedirectAgent(TrueHeadersAgent(reactor))
        headers = TrueHeaders({"Spam": ["ham"]})
        url = "http://httpbin.org/absolute-redirect/3"
        response = yield agent.request('GET', url, headers)
        body = yield readBody(response)
        j = json.loads(body)
        self.assertEqual(j['headers']['Spam'], 'ham')

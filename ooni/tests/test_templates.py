from ooni.templates import httpt

from twisted.internet.error import DNSLookupError
from twisted.internet import reactor, defer
from twisted.trial import unittest


class TestHTTPT(unittest.TestCase):
    def setUp(self):
        from twisted.web.resource import Resource
        from twisted.web.server import Site

        class DummyResource(Resource):
            isLeaf = True

            def render_GET(self, request):
                return "%s" % request.method

        r = DummyResource()
        factory = Site(r)
        self.port = reactor.listenTCP(8880, factory)

    def tearDown(self):
        self.port.stopListening()

    @defer.inlineCallbacks
    def test_do_request(self):
        http_test = httpt.HTTPTest()
        http_test.localOptions['socksproxy'] = None
        http_test._setUp()
        response = yield http_test.doRequest('http://localhost:8880/')
        assert response.body == "GET"
        assert len(http_test.report['requests']) == 1
        assert 'request' in http_test.report['requests'][0]
        assert 'response' in http_test.report['requests'][0]

    @defer.inlineCallbacks
    def test_do_failing_request(self):
        http_test = httpt.HTTPTest()
        http_test.localOptions['socksproxy'] = None
        http_test._setUp()
        yield self.assertFailure(http_test.doRequest('http://invaliddomain/'), DNSLookupError)
        assert http_test.report['requests'][0]['failure'] == 'dns_lookup_error'

from ooni.templates import httpt, dnst

from ooni.tests import is_internet_connected

from twisted.names import dns
from twisted.internet.error import DNSLookupError
from twisted.internet import reactor, defer, base
from twisted.trial import unittest

base.DelayedCall.debug = True

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

class TestDNST(unittest.TestCase):
    def setUp(self):
        if not is_internet_connected():
            self.skipTest("You must be connected to the internet to run this test")

    def test_represent_answer_a(self):
        a_record = dns.RRHeader(payload=dns.Record_A(address="1.1.1.1"),
                                type=dns.A)
        self.assertEqual(dnst.representAnswer(a_record),
                         {'ipv4': '1.1.1.1', 'answer_type': 'A'})

    def test_represent_answer_ptr(self):
        ptr_record = dns.RRHeader(payload=dns.Record_PTR(name="example.com"),
                                  type=dns.PTR)
        self.assertEqual(dnst.representAnswer(ptr_record),
                         {'hostname': 'example.com', 'answer_type': 'PTR'})

    def test_represent_answer_soa(self):
        ptr_record = dns.RRHeader(payload=dns.Record_SOA(mname='example.com',
                                                         rname='foo.example.com'),
                                  type=dns.SOA)
        represented_answer = {}
        represented_answer['ttl'] = None
        represented_answer['answer_type'] = 'SOA'
        represented_answer['hostname'] = 'example.com'
        represented_answer['responsible_name'] = 'foo.example.com'
        represented_answer['serial_number'] = 0
        represented_answer['refresh_interval'] = 0
        represented_answer['retry_interval'] = 0
        represented_answer['minimum_ttl'] = 0
        represented_answer['expiration_limit'] = 0
        self.assertEqual(dnst.representAnswer(ptr_record),
                         represented_answer)

    @defer.inlineCallbacks
    def test_perform_a_lookup(self):
        if not is_internet_connected():
            self.skipTest("You must be connected to the internet to run this test")
        dns_test = dnst.DNSTest()
        dns_test._setUp()
        result = yield dns_test.performALookup('example.com', dns_server=('8.8.8.8', 53))
        self.assertEqual(result, ['93.184.216.34'])

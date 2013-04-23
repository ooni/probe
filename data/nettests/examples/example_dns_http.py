from twisted.internet import defer
from ooni.templates import httpt, dnst

class TestDNSandHTTP(httpt.HTTPTest, dnst.DNSTest):

    @defer.inlineCallbacks
    def test_http_and_dns(self):
        yield self.doRequest('http://torproject.org')
        yield self.performALookup('torproject.org', ('8.8.8.8', 53))



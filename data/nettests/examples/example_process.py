from twisted.internet import defer

from ooni.templates import process


class TestProcessExample(process.ProcessTest):
    @defer.inlineCallbacks
    def test_http_and_dns(self):
        yield self.run(["echo", "Hello world!"])
        yield self.run(["sleep", "10"])

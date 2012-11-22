
from twisted.internet.error import ConnectionRefusedError
from ooni.utils import log
from ooni.templates import tcpt

class ExampleTCPT(tcpt.TCPTest):
    def test_hello_world(self):
        def got_response(response):
            print "Got this data %s" % response

        def connection_failed(failure):
            failure.trap(ConnectionRefusedError)
            print "Connection Refused"

        self.address = "127.0.0.1"
        self.port = 57002
        payload = "Hello World!\n\r"
        d = self.sendPayload(payload)
        d.addErrback(connection_failed)
        d.addCallback(got_response)
        return d

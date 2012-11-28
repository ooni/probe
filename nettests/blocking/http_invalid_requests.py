# -*- encoding: utf-8 -*-
from twisted.python import usage

from ooni.utils import randomStr
from ooni.templates import tcpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', '127.0.0.1:57002',
                        'The OONI backend that runs a TCP echo server (must be on port 80)']]

    optFlags = [['nopayloadmatch', 'n',
        "Don't match the payload of the response. This option is used when you don't have a TCP echo server running"]]

class HTTPInvalidRequests(tcpt.TCPTest):
    name = "HTTP Invalid Requests"
    version = "0.1.1"
    authors = "Arturo Filastò"

    inputFile = ['file', 'f', None,
                 'Input file of list of hostnames to attempt to resolve']

    usageOptions = UsageOptions
    requiredOptions = ['backend']

    def setUp(self):
        try:
            self.address, self.port = self.localOptions['backend'].split(":")
            self.port = int(self.port)
        except:
            raise usage.UsageError("Invalid backend address specified (must be address:port)")

    def test_random_invalid_request(self):
        """
        We test sending data to a TCP echo server, if what we get back is not
        what we have sent then there is tampering going on.
        This is for example what squid will return when performing such
        request:

            HTTP/1.0 400 Bad Request
            Server: squid/2.6.STABLE21
            Date: Sat, 23 Jul 2011 02:22:44 GMT
            Content-Type: text/html
            Content-Length: 1178
            Expires: Sat, 23 Jul 2011 02:22:44 GMT
            X-Squid-Error: ERR_INVALID_REQ 0
            X-Cache: MISS from cache_server
            X-Cache-Lookup: NONE from cache_server:3128
            Via: 1.0 cache_server:3128 (squid/2.6.STABLE21)
            Proxy-Connection: close

        """
        payload = randomStr(10) + "\n\r"
        def got_all_data(received_array):
            if not self.localOptions['nopayloadmatch']:
                first = received_array[0]
                if first != payload:
                    self.report['tampering'] = True
            else:
                self.report['tampering'] = 'unknown'

        d = self.sendPayload(payload)
        d.addCallback(got_all_data)
        return d

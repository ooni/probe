# -*- encoding: utf-8 -*-
from twisted.python import usage

from ooni.utils import log
from ooni.templates import tcpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', '127.0.0.1',
                        'The OONI backend that runs a TCP echo server'],
                    ['backendport', 'p', 80, 'Specify the port that the TCP echo server is running (should only be set for debugging)']]

class HTTPTrix(tcpt.TCPTest):
    name = "HTTPTrix"
    version = "0.1"
    authors = "Arturo Filastò"

    usageOptions = UsageOptions
    requiresTor = False
    requiresRoot = False
    requiredOptions = ['backend']

    def setUp(self):
        self.port = int(self.localOptions['backendport'])
        self.address = self.localOptions['backend']

    def check_for_manipulation(self, response, payload):
        log.debug("Checking if %s == %s" % (response, payload))
        if response != payload:
            self.report['tampering'] = True
        else:
            self.report['tampering'] = False

    def test_for_squid_cache_object(self):
        """
        This detects the presence of a squid transparent HTTP proxy by sending
        a request for cache_object://localhost/info.

        This tests for the presence of a Squid Transparent proxy by sending:

            GET cache_object://localhost/info HTTP/1.1
        """
        payload = 'GET cache_object://localhost/info HTTP/1.1'
        payload += '\n\r'

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d


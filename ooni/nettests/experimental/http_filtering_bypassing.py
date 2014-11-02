# -*- encoding: utf-8 -*-
from twisted.python import usage

from ooni.utils import log
from ooni.utils import randomStr
from ooni.templates import tcpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', '127.0.0.1',
                        'The OONI backend that runs a TCP echo server'],
                    ['backendport', 'p', 80, 'Specify the port that the TCP echo server is running (should only be set for debugging)']]

class HTTPFilteringBypass(tcpt.TCPTest):
    name = "HTTPFilteringBypass"
    version = "0.1"
    authors = "xx"

    inputFile = ['file', 'f', None,
            'Specify a list of hostnames to use as inputs']

    usageOptions = UsageOptions
    requiredOptions = ['backend']
    requiresRoot = False
    requiresTor = False

    def setUp(self):
        self.port = int(self.localOptions['backendport'])
        self.address = self.localOptions['backend']
        self.report['tampering'] = None

    def check_for_manipulation(self, response, payload):
        log.debug("Checking if %s == %s" % (response, payload))
        if response != payload:
            self.report['tampering'] = True
        else:
            self.report['tampering'] = False

    def test_prepend_newline(self):
        payload = "\nGET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_tab_trick(self):
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\t\n\r" % self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_subdomain_blocking(self):
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % randomStr(10) + '.' + self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_fuzzy_domain_blocking(self):
        hostname_field = randomStr(10) + '.' + self.input + '.' + randomStr(10)
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % hostname_field

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_fuzzy_match_blocking(self):
        hostname_field = randomStr(10) + self.input + randomStr(10)
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % hostname_field

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d

    def test_normal_request(self):
        payload = "GET / HTTP/1.1\n\r"
        payload += "Host: %s\n\r" % self.input

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload)
        return d


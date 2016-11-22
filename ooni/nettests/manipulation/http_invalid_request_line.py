# -*- encoding: utf-8 -*-
from twisted.python import usage

from ooni.utils import log
from ooni.utils import randomStr, randomSTR
from ooni.templates import tcpt


class UsageOptions(usage.Options):
    optParameters = [
        ['backend', 'b', None, 'The OONI backend that runs a TCP echo server.'],
        ['backendport', 'p', 80,
         'Specify the port that the TCP echo server is running '
         '(should only be set for debugging).']]


class HTTPInvalidRequestLine(tcpt.TCPTest):

    """
    The goal of this test is to do some very basic and not very noisy fuzzing
    on the HTTP request line. We generate a series of requests that are not
    valid HTTP requests.

    Unless elsewhere stated 'Xx'*N refers to N*2 random upper or lowercase
    ascii letters or numbers ('XxXx' will be 4).
    """
    name = "HTTP Invalid Request Line"
    description = "Performs out of spec HTTP requests in the attempt to "\
                  "trigger a proxy error message."
    version = "0.2"
    authors = "Arturo Filastò"

    usageOptions = UsageOptions

    requiredTestHelpers = {'backend': 'tcp-echo'}
    requiredOptions = ['backend']
    requiresRoot = False
    requiresTor = False

    def setUp(self):
        self.port = int(self.localOptions['backendport'])
        self.address = self.localOptions['backend']
        self.report['tampering'] = None

    def check_for_manipulation(self, response, payload, manipulation_type):
        log.debug("Checking if %s == %s" % (response, payload))
        if response != payload:
            log.msg("{0}: Detected manipulation!".format(manipulation_type))
            log.msg(response)
            self.report['tampering'] = True
        else:
            log.msg("{0}: No manipulation detected.".format(manipulation_type))
            self.report['tampering'] = False

    def test_random_invalid_method(self):
        """
        We test sending data to a TCP echo server listening on port 80, if what
        we get back is not what we have sent then there is tampering going on.
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
        payload = randomSTR(4) + " / HTTP/1.1\n\r"

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload, 'random_invalid_method')
        return d

    def test_random_invalid_field_count(self):
        """
        This generates a request that looks like this:

        XxXxX XxXxX XxXxX XxXxX

        This may trigger some bugs in the HTTP parsers of transparent HTTP
        proxies.
        """
        payload = ' '.join(randomStr(5) for x in range(4))
        payload += "\n\r"

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload, 'random_invalid_field_count')
        return d

    def test_random_big_request_method(self):
        """
        This generates a request that looks like this:

        Xx*512 / HTTP/1.1
        """
        payload = randomStr(1024) + ' / HTTP/1.1\n\r'

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload, 'random_big_request_method')
        return d

    def test_random_invalid_version_number(self):
        """
        This generates a request that looks like this:

        GET / HTTP/XxX
        """
        payload = 'GET / HTTP/' + randomStr(3)
        payload += '\n\r'

        d = self.sendPayload(payload)
        d.addCallback(self.check_for_manipulation, payload, 'random_invalid_version_number')
        return d

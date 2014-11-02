# -*- encoding: utf-8 -*-
#
# Squid transparent HTTP proxy detector
# *************************************
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni import utils
from ooni.utils import log
from ooni.templates import httpt
import re

class SquidTest(httpt.HTTPTest):
    """
    This test aims at detecting the presence of a squid based transparent HTTP
    proxy. It also tries to detect the version number.
    """
    name = "Squid test"
    author = "Arturo Filastò"
    version = "0.1"

    optParameters = [['backend', 'b', 'http://ooni.nu/test/', 'Test backend to use']]

    #inputFile = ['urls', 'f', None, 'Urls file']
    inputs =['http://google.com']

    requiresRoot = False
    requiresTor = False

    def test_cacheobject(self):
        """
        This detects the presence of a squid transparent HTTP proxy by sending
        a request for cache_object://localhost/info.

        The response to this request will usually also contain the squid
        version number.
        """
        log.debug("Running")
        def process_body(body):
            if "Access Denied." in body:
                self.report['transparent_http_proxy'] = True
            else:
                self.report['transparent_http_proxy'] = False

        log.msg("Testing Squid proxy presence by sending a request for "\
                "cache_object")
        headers = {}
        #headers["Host"] = [self.input]
        self.report['trans_http_proxy'] = None
        method = "GET"
        body = "cache_object://localhost/info"
        return self.doRequest(self.localOptions['backend'], method=method, body=body,
                        headers=headers, body_processor=process_body)

    def test_search_bad_request(self):
        """
        Attempts to perform a request with a random invalid HTTP method.

        If we are being MITMed by a Transparent Squid HTTP proxy we will get
        back a response containing the X-Squid-Error header.
        """
        def process_headers(headers):
            log.debug("Processing headers in test_search_bad_request")
            if 'X-Squid-Error' in headers:
                log.msg("Detected the presence of a transparent HTTP "\
                        "squid proxy")
                self.report['trans_http_proxy'] = True
            else:
                log.msg("Did not detect the presence of transparent HTTP "\
                        "squid proxy")
                self.report['transparent_http_proxy'] = False

        log.msg("Testing Squid proxy presence by sending a random bad request")
        headers = {}
        #headers["Host"] = [self.input]
        method = utils.randomSTR(10, True)
        self.report['transparent_http_proxy'] = None
        return self.doRequest(self.localOptions['backend'], method=method,
                        headers=headers, headers_processor=process_headers)

    def test_squid_headers(self):
        """
        Detects the presence of a squid transparent HTTP proxy based on the
        response headers it adds to the responses to requests.
        """
        def process_headers(headers):
            """
            Checks if any of the headers that squid is known to add match the
            squid regexp.

            We are looking for something that looks like this:

                via: 1.0 cache_server:3128 (squid/2.6.STABLE21)
                x-cache: MISS from cache_server
                x-cache-lookup: MISS from cache_server:3128
            """
            squid_headers = {'via': r'.* \((squid.*)\)',
                        'x-cache': r'MISS from (\w+)',
                        'x-cache-lookup': r'MISS from (\w+:?\d+?)'
                        }

            self.report['transparent_http_proxy'] = False
            for key in squid_headers.keys():
                if key in headers:
                    log.debug("Found %s in headers" % key)
                    m = re.search(squid_headers[key], headers[key])
                    if m:
                        log.msg("Detected the presence of squid transparent"\
                                " HTTP Proxy")
                        self.report['transparent_http_proxy'] = True

        log.msg("Testing Squid proxy by looking at response headers")
        headers = {}
        #headers["Host"] = [self.input]
        method = "GET"
        self.report['transparent_http_proxy'] = None
        d = self.doRequest(self.localOptions['backend'], method=method,
                        headers=headers, headers_processor=process_headers)
        return d



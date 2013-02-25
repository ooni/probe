# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.python import usage
from ooni.utils import log
from ooni.templates import httpt

class UsageOptions(usage.Options):
    optParameters = [
                     ['url', 'u', None, 'Specify a single URL to test.'],
                     ['factor', 'f', 0.8, 'What factor should be used for triggering censorship (0.8 == 80%)']
                    ]

class HTTPRequestsTest(httpt.HTTPTest):
    """
    Performs a two GET requests to the set of sites to be tested for
    censorship, one over a known good control channel (Tor), the other over the
    test network.

    We check to see if the response headers match and if the response body
    lengths match.
    """
    name = "HTTP Requests Test"
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, 
            'List of URLS to perform GET and POST requests to']

    # These values are used for determining censorship based on response body
    # lengths
    control_body_length = None
    experiment_body_length = None

    def setUp(self):
        """
        Check for inputs.
        """
        if self.input:
            self.url = self.input
        elif self.localOptions['url']:
            self.url = self.localOptions['url']
        else:
            raise Exception("No input specified")

        self.factor = self.localOptions['factor']

    def compare_body_lengths(self):
        body_length_a = self.control_body_length
        body_length_b = self.experiment_body_length

        if body_length_b == 0 and body_length_a != 0:
            rel = float(body_length_b)/float(body_length_a)
        elif body_length_b == 0 and body_length_a == 0:
            rel = float(1)
        else:
            rel = float(body_length_a)/float(body_length_b)

        if rel > 1:
            rel = 1/rel

        self.report['body_proportion'] = rel
        self.report['factor'] = self.factor
        if rel > self.factor:
            log.msg("The two body lengths appear to match")
            log.msg("censorship is probably not happening")
            self.report['body_length_match'] = True
        else:
            log.msg("The two body lengths appear to not match")
            log.msg("censorship could be happening")
            self.report['body_length_match'] = False

    def compare_headers(self):
        diff = TrueHeaders(self.control_headers).getDiff(self.experiment_headers)
        if diff:
            log.msg("Headers appear to match")
            self.report['headers_match'] = False
        else:
            log.msg("Headers appear to *not* match")
            self.report['headers_match'] = True

    def test_get(self):
        def errback(failure):
            log.err("There was an error while testing %s" % self.url)
            log.exception(failure)

        def control_body(result):
            """
            Callback for processing the control HTTP body response.
            """
            self.control_body_length = len(result)
            if self.experiment_body_length is not None:
                self.compare_body_lengths()

        def experiment_body(result):
            """
            Callback for processing the experiment HTTP body response.
            """
            self.experiment_body_length = len(result)
            if self.control_body_length is not None:
                self.compare_body_lengths()

        def control_headers(headers_dict):
            """
            Callback for processing the control HTTP headers response.
            """
            self.control_headers = headers_dict

        def experiment_headers(headers_dict):
            """
            Callback for processing the experiment HTTP headers response.
            """
            self.experiment_headers = headers_dict

        l = []
        log.msg("Performing GET request to %s" % self.url)
        experiment_request = self.doRequest(self.url, method="GET",
                body_processor=experiment_body,
                headers_processor=control_headers)

        log.msg("Performing GET request to %s via Tor" % self.url)
        control_request = self.doRequest(self.url, method="GET",
                use_tor=True, body_processor=control_body,
                headers_processor=control_headers)

        l.append(experiment_request)
        l.append(control_request)
        dl = defer.DeferredList(l)
        return dl


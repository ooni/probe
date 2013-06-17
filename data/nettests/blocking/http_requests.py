# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from twisted.internet import defer
from twisted.python import usage

from ooni.utils import log
from ooni.utils.net import userAgents
from ooni.templates import httpt
from ooni.errors import failureToString, handleAllFailures

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
    version = "0.2.3"

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
        self.report['control_failure'] = None
        self.report['experiment_failure'] = None

    def compare_body_lengths(self, body_length_a, body_length_b):

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

    def compare_headers(self, headers_a, headers_b):
        diff = headers_a.getDiff(headers_b)
        if diff:
            log.msg("Headers appear to *not* match")
            self.report['headers_diff'] = diff
            self.report['headers_match'] = False
        else:
            log.msg("Headers appear to match")
            self.report['headers_diff'] = diff
            self.report['headers_match'] = True

    def test_get(self):
        def callback(res):
            experiment, control = res
            experiment_succeeded, experiment_result = experiment
            control_succeeded, control_result = control

            if control_succeeded and experiment_succeeded:
                self.compare_body_lengths(len(experiment_result.body),
                        len(control_result.body))

                self.compare_headers(control_result.headers,
                        experiment_result.headers)

            if not control_succeeded:
                self.report['control_failure'] = failureToString(control_result)

            if not experiment_succeeded:
                self.report['experiment_failure'] = failureToString(experiment_result)

        headers = {'User-Agent': [random.choice(userAgents)]}

        l = []
        log.msg("Performing GET request to %s" % self.url)
        experiment_request = self.doRequest(self.url, method="GET",
                headers=headers)

        log.msg("Performing GET request to %s via Tor" % self.url)
        control_request = self.doRequest(self.url, method="GET",
                use_tor=True, headers=headers)

        l.append(experiment_request)
        l.append(control_request)

        dl = defer.DeferredList(l, consumeErrors=True)
        dl.addCallback(callback)

        return dl


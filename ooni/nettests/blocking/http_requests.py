# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from twisted.python import usage, failure

from ooni.utils import log
from ooni.utils.net import userAgents
from ooni.templates import httpt
from ooni.errors import failureToString

class MissingInput(Exception):
    pass

class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test.'],
        ['factor', 'f', 0.8,
         'What factor should be used for triggering censorship '
         '(0.8 == 80%).']]
    optFlags = [
        ["withoutbody", "B", "don't include HTTP response body inside of the "
         "report."],
        ]


class HTTPRequestsTest(httpt.HTTPTest):

    """
    Performs a two GET requests to the set of sites to be tested for
    censorship, one over a known good control channel (Tor), the other over the
    test network.

    We check to see if the response headers match and if the response body
    lengths match.
    """
    name = "HTTP Requests"
    description = ("Performs a HTTP GET request over Tor and one over the "
                  "local network and compares the two results.")
    author = "Arturo Filastò"
    version = "0.2.5"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'List of URLS to perform GET and POST requests to']
    requiresRoot = False
    requiresTor = True

    # These values are used for determining censorship based on response body
    # lengths
    control_body_length = None
    experiment_body_length = None

    def requirements(self):
        if not self.localOptions['url'] and \
                not self.localOptions['file']:
            raise MissingInput("You did not specify either a URL with -u "
                               "or an input file with -f")

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
        self.report['input'] = self.url

        self.factor = self.localOptions['factor']
        self.report['control_failure'] = None
        self.report['experiment_failure'] = None
        self.report['body_length_match'] = None
        self.report['body_proportion'] = None
        self.report['factor'] = float(self.factor)
        self.report['headers_diff'] = None
        self.report['headers_match'] = None
        self.report['control_cloudflare'] = None

        self.headers = {'User-Agent': [random.choice(userAgents)]}

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
        if rel > float(self.factor):
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

    def test_get_experiment(self):
        log.msg("Performing GET request to %s" % self.url)
        return self.doRequest(self.url, method="GET",
                              use_tor=False, headers=self.headers)

    def test_get_control(self):
        log.msg("Performing GET request to %s over Tor" % self.url)
        return self.doRequest(self.url, method="GET",
                              use_tor=True, headers=self.headers)

    def postProcessor(self, measurements):
        experiment = control = None
        for status, measurement in measurements:
            net_test_method = measurement.netTestMethod.im_func.func_name

            if net_test_method == "test_get_experiment":
                if isinstance(measurement.result, failure.Failure):
                    self.report['experiment_failure'] = failureToString(
                        measurement.result)
                else:
                    experiment = measurement.result
            elif net_test_method == "test_get_control":
                if isinstance(measurement.result, failure.Failure):
                    self.report['control_failure'] = failureToString(
                        measurement.result)
                else:
                    control = measurement.result

        if experiment and control:
            if hasattr(experiment, 'body') and hasattr(control, 'body') \
                    and experiment.body and control.body:
                self.report['control_cloudflare'] = False
                if 'Attention Required! | CloudFlare' in control.body:
                    log.msg("The control body contains a blockpage from "
                            "cloudflare. This will skew our results.")
                    self.report['control_cloudflare'] = True
                self.compare_body_lengths(len(control.body),
                                          len(experiment.body))
            if hasattr(experiment, 'headers') and hasattr(control, 'headers') \
                    and experiment.headers and control.headers:
                self.compare_headers(control.headers,
                                     experiment.headers)
        return self.report

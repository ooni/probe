# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.internet import defer
from twisted.python import usage
from ooni.templates import httpt

class UsageOptions(usage.Options):
    optParameters = [
                     ['url', 'u', None, 'Specify a single URL to test.'],
                     ['factor', 'f', 0.8, 'What factor should be used for triggering censorship (0.8 == 80%)']
                    ]

class HTTPBodyLength(httpt.HTTPTest):
    """
    Performs a two GET requests to the set of sites to be tested for
    censorship, one over a known good control channel (Tor), the other over the
    test network.
    We then look at the response body lengths and see if the control response
    differs from the experiment response by a certain factor.
    """
    name = "HTTP Body length test"
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

        rel = float(body_length_a)/float(body_length_b)
        if rel > 1:
            rel = 1/rel

        self.report['body_proportion'] = rel
        self.report['factor'] = self.factor
        if rel < self.factor:
            self.report['censorship'] = True
        else:
            self.report['censorship'] = False

    def test_get(self):
        def errback(failure):
            log.err("There was an error while testing %s" % self.url)
            log.exception(failure)

        def control_body(result):
            self.control_body_length = len(result)
            if self.experiment_body_length:
                self.compare_body_lengths()

        def experiment_body(result):
            self.experiment_body_length = len(result)
            if self.control_body_length:
                self.compare_body_lengths()

        dl = []
        experiment_request = self.doRequest(self.url, method="GET",
                body_processor=experiment_body)
        control_request = self.doRequest(self.url, method="GET",
                use_tor=True, body_processor=control_body)
        dl.append(experiment_request)
        dl.append(control_request)
        d = defer.DeferredList(dl)
        return d


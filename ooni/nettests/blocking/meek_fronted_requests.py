# -*- encoding: utf-8 -*-
#
# :licence: see LICENSE

from twisted.python import usage
from ooni.templates import httpt
from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [ ['expectedBody', 'B',
                         'I’m just a happy little web server.\n',
                          'Expected body content from GET response.'],
                      ['domainName', 'D', None,
                        'Specify a single fronted domainName to test.'],
                      ['hostHeader', 'H', None,
                        'Specify "inside" Host Header to test.']
                    ]

class meekTest(httpt.HTTPTest):
    """
    Performs a HTTP GET request to a list of fronted domains with the Host
    Header of the "inside" meek-server. The meek-server handles a GET request
    and response with: "I’m just a happy little web server.\n".
    The input file should be formatted as (one per line):
    "domainName:hostHeader"
    ajax.aspnetcdn.com:az668014.vo.msecnd.net
    a0.awsstatic.com:d2zfqthxsdq309.cloudfront.net

    """
    name = "Meek fronted requests test"
    description = "This tests for the Meek Tor pluggable transport "\
                  "frontend reachability."
    version = "0.0.1"

    usageOptions = UsageOptions
    inputFile = ['file', 'f', None,
                  "File containing the domainName:hostHeader combinations to\
                  be tested, one per line."]
    inputs = [('ajax.aspnetcdn.com', 'az668014.vo.msecnd.net'),
               ('a0.awsstatic.com', 'd2zfqthxsdq309.cloudfront.net')]

    requiresRoot = False
    requiresTor = False

    def setUp(self):
        """
        Check for inputs.
        """

        if self.input:
           if (isinstance(self.input, tuple) or isinstance(self.input, list)):
               self.domainName, self.header = self.input
           else:
               self.domainName, self.header = self.input.split(':')
        elif (self.localOptions['domainName'] and
              self.localOptions['hostHeader']):
               self.domainName = self.localOptions['domainName']
               self.header = self.localOptions['hostHeader']

        self.expectedBody = self.localOptions['expectedBody']
        self.domainName = 'https://' + self.domainName

    def test_meek_response(self):
        """
        Detects if the fronted request is blocked.
        """
        log.msg("Testing fronted domain:%s with Host Header:%s"
                % (self.domainName, self.header))
        def process_body(body):
            if self.expectedBody != body:
                self.report['success'] = False
            else:
                self.report['success'] = True

        headers = {}
        headers['Host'] = [self.header]
        return self.doRequest(self.domainName, method="GET", headers=headers,
                              body_processor=process_body)


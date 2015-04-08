# -*- encoding: utf-8 -*-
#
# :licence: see LICENSE

from twisted.python import usage
from ooni.templates import httpt
from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [ ['ExpectedBody', 'B',
                         'I’m just a happy little web server.\n',
                          'Expected body content from GET response'],
                      ['DomainName', 'D', None,
                        'Specify a single fronted DomainName to test.'],
                      ['HostHeader', 'H', None,
                        'Specify "inside" Host Header to test.']
                    ]

class meekTest(httpt.HTTPTest):
    """
    Performs a HTTP GET request to a list of fronted domains with the Host
    Header of the "inside" meek-server. The meek-server handles a GET request
    and response with: "I’m just a happy little web server.\n".
    The input file should be formatted as (one per line):
    "DomainName:HostHeader"

    Some default meek DomainName and HostHeader combinations:
    www.google.com:meek-reflect.appspot.com
    ajax.aspnetcdn.com:az668014.vo.msecnd.net
    a0.awsstatic.com:d2zfqthxsdq309.cloudfront.net
    """
    name = "meek fronted requests test"
    version = "0.0.1"

    usageOptions = UsageOptions
    inputFile = ['file', 'f', None,
                  "File containing the DomainName:HostHeader combinations to\
                  be tested, one per line."]

    requiresRoot = False
    requiresTor = False

    def setUp(self):
        """
        Check for inputs.
        """
        if self.input:
            self.DomainName, self.header = self.input.split(':')
        elif (self.localOptions['DomainName'] and
              self.localOptions['HostHeader']):
               self.DomainName = self.localOptions['DomainName']
               self.header = self.localOptions['HostHeader']
        else:
            raise Exception("No input specified")

        self.ExpectedBody = self.localOptions['ExpectedBody']
        self.DomainName = 'https://' + self.DomainName

    def test_meek_response(self):
        """
        Detects if the fronted request is blocked.
        """
        log.msg("Testing fronted domain:%s with Host Header:%s"
                % (self.DomainName, self.header))
        def process_body(body):
            if self.ExpectedBody != body:
                self.report['success'] = False
            else:
                self.report['success'] = True

        headers = {}
        headers['Host'] = [self.header]
        return self.doRequest(self.DomainName, method="GET", headers=headers,
                              body_processor=process_body)

# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
import json
import yaml

from twisted.python import usage

from ooni.utils import log, net, randomStr
from ooni.templates import httpt
from ooni.common.txextra import TrueHeaders


def random_capitalization(string):
    output = ""
    original_string = string
    string = string.swapcase()
    for i in range(len(string)):
        if random.randint(0, 1):
            output += string[i].swapcase()
        else:
            output += string[i]
    if original_string == output:
        return random_capitalization(output)
    else:
        return output


class UsageOptions(usage.Options):
    optParameters = [
        ['backend', 'b', None,
         'URL of the backend to use for sending the requests.'],
        ['headers', 'h', None,
         'Specify a yaml formatted file from which to read '
         'the request headers to send.']
        ]


class HTTPHeaderFieldManipulation(httpt.HTTPTest):

    """
    It performes HTTP requests with request headers that vary capitalization
    towards a backend. If the headers reported by the server differ from
    the ones we sent, then we have detected tampering.
    """
    name = "HTTP Header Field Manipulation"
    description = "Checks if the HTTP request the server " \
                  "sees is the same as the one that the client has created."
    author = "Arturo Filastò"
    version = "0.1.5"

    randomizeUA = False
    usageOptions = UsageOptions

    requiredTestHelpers = {'backend': 'http-return-json-headers'}
    requiredOptions = ['backend']
    requiresTor = False
    requiresRoot = False

    def setUp(self):
        super(HTTPHeaderFieldManipulation, self).setUp()
        self.url = self.localOptions['backend']

    def get_headers(self):
        headers = {}
        if self.localOptions['headers']:
            try:
                f = open(self.localOptions['headers'])
            except IOError:
                raise Exception("Specified input file does not exist")
            content = ''.join(f.readlines())
            f.close()
            headers = yaml.safe_load(content)
            return headers
        else:
            # XXX generate these from a random choice taken from
            # whatheaders.com
            # http://s3.amazonaws.com/data.whatheaders.com/whatheaders-latest.xml.zip
            headers = {
                "User-Agent": [
                    random.choice(
                        net.userAgents)],
                "Accept": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
                "Accept-Encoding": ["gzip,deflate,sdch"],
                "Accept-Language": ["en-US,en;q=0.8"],
                "Accept-Charset": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
                "Host": [
                    randomStr(15) +
                    '.com']}
            return headers

    def get_random_caps_headers(self):
        headers = {}
        normal_headers = self.get_headers()
        for k, v in normal_headers.items():
            new_key = random_capitalization(k)
            headers[new_key] = v
        return headers

    def processResponseBody(self, data):
        self.check_for_tampering(data)

    def check_for_tampering(self, data):
        """
        Here we do checks to verify if the request we made has been tampered
        with. We have 3 categories of tampering:

        *  **total** when the response is not a json object and therefore we were not
        able to reach the ooniprobe test backend

        *  **request_line_capitalization** when the HTTP Request line (e.x. GET /
        HTTP/1.1) does not match the capitalization we set.

        *  **header_field_number** when the number of headers we sent does not match
        with the ones the backend received

        *  **header_name_capitalization** when the header field names do not match
        those that we sent.

        *  **header_field_value** when the header field value does not match with the
        one we transmitted.

        """
        log.msg("Checking for tampering on %s" % self.url)

        self.report['tampering'] = {
            'total': False,
            'request_line_capitalization': False,
            'header_name_capitalization': False,
            'header_field_value': False,
            'header_field_number': False
        }
        try:
            response = json.loads(data)
        except ValueError:
            self.report['tampering']['total'] = True
            return

        request_request_line = "%s / HTTP/1.1" % self.request_method

        try:
            response_request_line = response['request_line']
            response_headers_dict = response['headers_dict']
        except KeyError:
            self.report['tampering']['total'] = True
            return

        if request_request_line != response_request_line:
            self.report['tampering']['request_line_capitalization'] = True

        request_headers = TrueHeaders(self.request_headers)
        diff = request_headers.getDiff(TrueHeaders(response_headers_dict),
                                       ignore=['Connection'])
        if diff:
            self.report['tampering']['header_field_name'] = True
        else:
            self.report['tampering']['header_field_name'] = False
        self.report['tampering']['header_name_diff'] = list(diff)
        log.msg("    total: %(total)s" % self.report['tampering'])
        log.msg(
            "    request_line_capitalization: %(request_line_capitalization)s" %
            self.report['tampering'])
        log.msg(
            "    header_name_capitalization: %(header_name_capitalization)s" %
            self.report['tampering'])
        log.msg(
            "    header_field_value: %(header_field_value)s" %
            self.report['tampering'])
        log.msg(
            "    header_field_number: %(header_field_number)s" %
            self.report['tampering'])

    def test_get_random_capitalization(self):
        self.request_method = random_capitalization("GET")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                              headers=self.request_headers)

# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
import json

from twisted.python import usage

from ooni.utils import log, net, randomStr
from ooni.templates import httpt

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
            ['backend', 'b', 'http://127.0.0.1:57001', 
                'URL of the backend to use for sending the requests'],
            ['headers', 'h', None,
                'Specify a yaml formatted file from which to read the request headers to send']
            ]

class HTTPRequests(httpt.HTTPTest):
    """
    This test is also known as Header Field manipulation. It performes HTTP
    requests with variations in capitalization towards the backend.
    """
    name = "HTTP Requests"
    author = "Arturo Filastò"
    version = "0.1.1"

    randomizeUA = False
    usageOptions = UsageOptions

    requiredOptions = ['backend']

    def processInputs(self):
        if self.localOptions['backend']:
            self.url = self.localOptions['backend']
        else:
            raise Exception("No backend specified")

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
        self.report['tampering'] = {'total': False,
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

        requestLine = "%s / HTTP/1.1" % self.request_method
        if response['request_line'] != requestLine:
            self.report['tampering']['request_line_capitalization'] = True

        # We compare against length -1 because the response will also contain
        # the Connection: close header since we do not do persistent
        # connections
        if len(self.request_headers) != (len(response['headers_dict']) - 1):
            self.report['tampering']['header_field_number'] = True

        for header, value in self.request_headers.items():
            # XXX this still needs some work
            # in particular if the response headers are of different length or
            # some extra headers get added in the response (so the lengths
            # match), we will get header_name_capitalization set to true, while
            # the actual tampering is the addition of an extraneous header
            # field.
            if header == "Connection":
                # Ignore Connection header
                continue
            try:
                response_value = response['headers_dict'][header]
                if response_value != value[0]:
                    log.msg("Tampering detected because %s != %s" % (response_value, value[0]))
                    self.report['tampering']['header_field_value'] = True
            except KeyError:
                log.msg("Tampering detected because %s not in %s" % (header, response['headers_dict']))
                self.report['tampering']['header_name_capitalization'] = True

    def get_headers(self):
        headers = {}
        if self.localOptions['headers']:
            # XXX test this code
            try:
                f = open(self.localOptions['headers'])
            except IOError:
                raise Exception("Specified input file does not exist")
            content = ''.join(f.readlines())
            f.close()
            headers = yaml.load(content)
            return headers
        else:
            headers = {"User-Agent": [random.choice(net.userAgents)[0]],
                "Accept": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
                "Accept-Encoding": ["gzip,deflate,sdch"],
                "Accept-Language": ["en-US,en;q=0.8"],
                "Accept-Charset": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"],
                "Host": [randomStr(15)+'.com']
            }
            return headers

    def get_random_caps_headers(self):
        headers = {}
        normal_headers = self.get_headers()
        for k, v in normal_headers.items():
            new_key = random_capitalization(k)
            headers[new_key] = v
        return headers

    def test_get(self):
        self.request_method = "GET"
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def test_get_random_capitalization(self):
        self.request_method = random_capitalization("GET")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def test_post(self):
        self.request_method = "POST"
        self.request_headers = self.get_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def test_post_random_capitalization(self):
        self.request_method = random_capitalization("POST")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def test_put(self):
        self.request_method = "PUT"
        self.request_headers = self.get_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def test_put_random_capitalization(self):
        self.request_method = random_capitalization("PUT")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)



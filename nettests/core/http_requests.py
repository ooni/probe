# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
import json

from twisted.python import usage

from ooni.utils import log, net
from ooni.templates import httpt

def random_capitalization(string):
    output = ""
    string = string.swapcase()
    for i in range(len(string)):
        if random.randint(0, 1):
            output += string[i].swapcase()
        else:
            output += string[i]
    return output

class UsageOptions(usage.Options):
    optParameters = [
            ['backend', 'b', None, 
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
    version = 0.1

    usageOptions = UsageOptions

    requiredOptions = ['backend']

    def processInputs(self):
        if self.localOptions['backend']:
            self.url = self.localOptions['backend']
        else:
            raise Exception("No backend specified")

    def processResponseBody(self, data):
        try:
            response = json.loads(data)
        except ValueError:
            self.report['tampering'] = True

        # XXX add checks for validation of sent headers

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
            headers = {"User-Agent": [random.choice(net.userAgents)],
                "Accept": ["text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"],
                "Accept-Encoding": ["gzip,deflate,sdch"],
                "Accept-Language": ["en-US,en;q=0.8"],
                "Accept-Charset": ["ISO-8859-1,utf-8;q=0.7,*;q=0.3"]}
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

    def a_test_get_random_capitalization(self):
        self.request_method = random_capitalization("GET")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def a_test_post(self):
        self.request_method = "POST"
        self.request_headers = self.get_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def a_test_post_random_capitalization(self):
        self.request_method = random_capitalization("POST")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def a_test_put(self):
        self.request_method = "PUT"
        self.request_headers = self.get_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)

    def test_put_random_capitalization(self):
        self.request_method = random_capitalization("PUT")
        self.request_headers = self.get_random_caps_headers()
        return self.doRequest(self.url, self.request_method,
                headers=self.request_headers)



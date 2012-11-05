# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.utils import log
from ooni.templates import httpt

class ExampleHTTP(httpt.HTTPTest):
    name = "Example HTTP Test"
    author = "Arturo Filastò"
    version = 0.1

    inputs = ['http://google.com/', 'http://wikileaks.org/',
              'http://torproject.org/']

    def test_http(self):
        if self.input:
            url = self.input
            return self.doRequest(url)
        else:
            raise Exception("No input specified")

    def processResponseBody(self, body):
        # XXX here shall go your logic
        #     for processing the body
        if 'blocked' in body:
            self.report['censored'] = True
        else:
            self.report['censored'] = False

    def processResponseHeaders(self, headers):
        # XXX place in here all the logic for handling the processing of HTTP
        #     Headers.
        pass


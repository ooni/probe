# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.templates import http
class Example(http.HTTPTest):
    inputs = ['http://google.com/', 'http://wikileaks.org/',
            'http://torproject.org/']

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
        if headers.hasHeader('location'):
            self.report['redirect'] = True

        server = headers.getRawHeaders("Server")
        if server:
            self.report['http_server'] = str(server.pop())


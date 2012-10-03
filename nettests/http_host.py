# -*- encoding: utf-8 -*-
#
# HTTP Host Test
# **************
#
# for more details see:
# https://trac.torproject.org/projects/tor/wiki/doc/OONI/Tests/HTTPHost
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from ooni.templates import httpt

good_http_server = "http://127.0.0.1:8090/"

class HTTPHost(httpt.HTTPTest):
    name = "HTTP Host"
    author = "Arturo Filastò"
    version = 0.1


    inputs = ['google.com', 'wikileaks.org',
              'torproject.org']

    def test_send_host_header(self):
        headers = {}
        headers["Host"] = [self.input]
        return self.doRequest(good_http_server, headers=headers)

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


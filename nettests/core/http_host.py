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

class HTTPHost(httpt.HTTPTest):
    name = "HTTP Host"
    author = "Arturo Filastò"
    version = 0.1

    optParameters = [['url', 'u', 'http://torproject.org/', 'Test single site'],
                     ['backend', 'b', 'http://ooni.nu/test/', 'Test backend to use'],
                     ]

    inputFile = ['urls', 'f', None, 'Urls file']

    def test_send_host_header(self):
        headers = {}
        headers["Host"] = [self.input]
        return self.doRequest(self.localOptions['backend'], headers=headers)

    def processResponseBody(self, body):
        if 'not censored' in body:
            self.report['trans_http_proxy'] = False
        else:
            self.report['trans_http_proxy'] = True


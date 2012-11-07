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

class UsageOptions(usage.Options):
    optParameters = [
                     ['url', 'u', 'http://torproject.org/', 'Test single site'],
                     ['backend', 'b', 'http://ooni.nu/test/', 'Test backend to use'],
                    ]


class HTTPHost(httpt.HTTPTest):
    """
    This test is aimed at detecting the presence of a transparent HTTP proxy
    and enumerating the sites that are being censored by it.
    """
    name = "HTTP Host"
    author = "Arturo Filastò"
    version = 0.1

    inputFile = ['urls', 'f', None, 'Urls file']

    def test_send_host_header(self):
        """
        Stuffs the HTTP Host header field with the site to be tested for
        censorship and does an HTTP request of this kind to our backend.

        We randomize the HTTP User Agent headers.
        """
        headers = {}
        headers["Host"] = [self.input]
        return self.doRequest(self.localOptions['backend'], headers=headers)

    def processResponseBody(self, body):
        """
        XXX this is to be filled in with either a domclass based classified or
        with a rule that will allow to detect that the body of the result is
        that of a censored site.
        """
        if 'not censored' in body:
            self.report['trans_http_proxy'] = False
        else:
            self.report['trans_http_proxy'] = True


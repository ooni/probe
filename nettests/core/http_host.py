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

import json
from twisted.python import usage

from ooni.utils import log
from ooni.templates import httpt

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', 'http://127.0.0.1:1234', 
                        'URL of the test backend to use'],
                     ['content', 'c', None, 
                        'The file to read from containing the content of a block page']]

class HTTPHost(httpt.HTTPTest):
    """
    This test is aimed at detecting the presence of a transparent HTTP proxy
    and enumerating the sites that are being censored by it.
    """
    name = "HTTP Host"
    author = "Arturo Filastò"
    version = "0.2"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, 'List of hostnames to test for censorship']

    requiredOptions = ['backend']

    def test_send_host_header(self):
        """
        Stuffs the HTTP Host header field with the site to be tested for
        censorship and does an HTTP request of this kind to our backend.

        We randomize the HTTP User Agent headers.
        """
        headers = {}
        headers["Host"] = [self.input]
        return self.doRequest(self.localOptions['backend'], headers=headers)

    def check_for_censorship(self, body):
        """
        If we have specified what a censorship page looks like here we will
        check if the page we are looking at matches it.

        XXX this is not tested, though it is basically what was used to detect
        censorship in the palestine case.
        """
        if self.localOptions['content']:
            self.report['censored'] = True

            censorship_page = open(self.localOptions['content'])
            response_page = iter(body.split("\n"))

            for censorship_line in censorship_page.xreadlines():
                response_line = response_page.next()
                if response_line != censorship_line:
                    self.report['censored'] = False
                    break

            censorship_page.close()

    def processResponseBody(self, body):
        """
        XXX this is to be filled in with either a domclass based classified or
        with a rule that will allow to detect that the body of the result is
        that of a censored site.
        """
        # If we don't see a json array we know that something is wrong for
        # sure
        if not body.startswith("{"):
            self.report['transparent_http_proxy'] = True
            self.check_for_censorship(body)
            return
        try:
            content = json.loads(body)
        except:
            log.debug("The json does not parse, this is not what we expected")
            self.report['trans_http_proxy'] = True
            self.check_for_censorship(body)
            return

        # We base the determination of the presence of a transparent HTTP
        # proxy on the basis of the response containing the json that is to be
        # returned by a HTTP Request Test Helper
        if 'request_method' in content and \
                'request_uri' in content and \
                'request_headers' in content:
            log.debug("Found the keys I expected in %s" % content)
            self.report['trans_http_proxy'] = False
        else:
            log.debug("Did not find the keys I expected in %s" % content)
            self.report['trans_http_proxy'] = True

        self.check_for_censorship(body)

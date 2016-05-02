# -*- encoding: utf-8 -*-
#
# HTTP Host Test
# **************
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import sys
import json
from twisted.internet import defer
from twisted.python import usage

from ooni.utils import randomStr

from ooni.utils import log
from ooni.templates import httpt


class UsageOptions(usage.Options):
    optParameters = [
        ['backend', 'b', None,
         'URL of the test backend to use. Should be listening on port 80 '
         'and be a HTTPReturnJSONHeadersHelper (ex. http://1.1.1.1).'],
        ['content', 'c', None, 'The file to read from containing the '
         'content of a block page.']
        ]


class HTTPHost(httpt.HTTPTest):

    """
    This test performs various manipulations of the HTTP Host header field and
    attempts to detect which filter bypassing strategies will work against the
    censor.

    Usually this test should be run with a list of sites that are known to be
    blocked inside of a particular network to assess which filter evasion
    strategies will work.
    """
    name = "HTTP Host"
    description = "Tests a variety of different filter bypassing techniques "\
                  "based on the HTTP Host header field."
    author = "Arturo Filastò"
    version = "0.2.4"

    randomizeUA = False
    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'List of hostnames to test for censorship.']

    requiredTestHelpers = {'backend': 'http-return-json-headers'}
    requiredOptions = ['backend', 'file']
    requiresTor = False
    requiresRoot = False

    def setUp(self):
        self.report['transparent_http_proxy'] = False

    def check_for_censorship(self, body, test_name):
        """
        XXX this is to be filled in with either a domclass based classified or
        with a rule that will allow to detect that the body of the result is
        that of a censored site.
        """
        # If we don't see a json dict we know that something is wrong for
        # sure
        if not body.startswith("{"):
            log.msg("This does not appear to be JSON")
            self.report['transparent_http_proxy'] = True
            return
        try:
            content = json.loads(body)
        except:
            log.msg("The json does not parse, this is not what we expected")
            self.report['transparent_http_proxy'] = True
            return

        # We base the determination of the presence of a transparent HTTP
        # proxy on the basis of the response containing the json that is to be
        # returned by a HTTP Request Test Helper
        if 'request_headers' in content and \
                'request_line' in content and \
                'headers_dict' in content:
            log.msg("Found the keys I expected in %s" % content)
            self.report['transparent_http_proxy'] = self.report[
                'transparent_http_proxy'] | False
            self.report[test_name] = False
        else:
            log.msg("Did not find the keys I expected in %s" % content)
            self.report['transparent_http_proxy'] = True
            if self.localOptions['content']:
                self.report[test_name] = True
                censorship_page = open(self.localOptions['content'])
                response_page = iter(body.split("\n"))

                for censorship_line in censorship_page:
                    response_line = response_page.next()
                    if response_line != censorship_line:
                        self.report[test_name] = False
                        break

                censorship_page.close()

    @defer.inlineCallbacks
    def test_filtering_prepend_newline_to_method(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [self.input]
        response = yield self.doRequest(self.localOptions['backend'],
                                        method="\nGET",
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_filtering_add_tab_to_host(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [self.input + '\t']
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_filtering_of_subdomain(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [randomStr(10) + '.' + self.input]
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_filtering_via_fuzzy_matching(self):
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [randomStr(10) + self.input + randomStr(10)]
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    @defer.inlineCallbacks
    def test_send_host_header(self):
        """
        Stuffs the HTTP Host header field with the site to be tested for
        censorship and does an HTTP request of this kind to our backend.

        We randomize the HTTP User Agent headers.
        """
        test_name = sys._getframe().f_code.co_name.replace('test_', '')
        headers = {}
        headers["Host"] = [self.input]
        response = yield self.doRequest(self.localOptions['backend'],
                                        headers=headers)
        self.check_for_censorship(response.body, test_name)

    def inputProcessor(self, filename=None):
        """
        This inputProcessor extracts domain names from urls
        """
        if filename:
            fp = open(filename)
            for x in fp.readlines():
                yield x.strip().split('//')[-1].split('/')[0]
            fp.close()
        else:
            pass

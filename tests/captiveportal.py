# -*- coding: utf-8 -*-
"""
    captiveportal
    *************

    This test is a collection of tests to detect the presence of a
    captive portal. Code is taken, in part from the old ooni-probe,
    which was written by Jacob Appelbaum and Arturo Filastò.

    :copyright: (c) 2012 Isis Lovecruft
    :license: see LICENSE for more details
"""
import os
import re
import urllib2
from urlparse import urlparse

from plugoo.assets import Asset
from plugoo.tests import Test

try:
    from gevent import monkey
    monkey.patch_socket()
except ImportError:
    print "The gevent module was not found. https://crate.io/packages/gevent/"

__plugoo__ = "captiveportal"
__desc__ = "Captive portal detection test"

class CaptivePortalAsset(Asset):
    """
    Parses captive_portal_tests.txt into an Asset.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

    def parse_line(self, line):
        self = Asset.parse_line(self, line)
        return line.replace('\n', '').split(', ')

class CaptivePortal(Test):
    """
    Compares content and status codes of HTTP responses, and attempts
    to determine if content has been altered.

    TODO: compare headers, random URL requests with control obtained
    through Tor.
    """
    def __init__(self, ooni):
        Test.__init__(self, ooni, name='test')
        self.default_ua = ooni.config.tests.default_ua

    def http_fetch(self, url, headers=None):
        """
        Parses an HTTP url, fetches it, and returns a urllib2 response
        object.
        """
        url = urlparse(url).geturl()
        request = urllib2.Request(url, None, headers)
        response = urllib2.urlopen(request)
        return response
 
    def http_content_match_fuzzy_opt(self, experimental_url, control_result,
                                     headers=None, fuzzy=False):
        """
        Makes an HTTP request on port 80 for experimental_url, then
        compares the response_content of experimental_url with the
        control_result. Optionally, if the fuzzy parameter is set to
        True, the response_content is compared with a regex of the
        control_result. If the response_content from the
        experimental_url and the control_result match, returns True
        with the HTTP status code, False and status code if otherwise.
        """
        log = self.logger

        if headers is None:
            default_ua = self.default_ua
            headers = {'User-Agent': default_ua}

        response = self.http_fetch(experimental_url, headers)
        response_content = response.read()
        response_code = response.code
        if response_content is not None:
            if fuzzy:
                pattern = re.compile(control_result)
                match = pattern.search(response_content)
                if not match:
                    log.info("Fuzzy HTTP content comparison of experiment" \
                                    " URL '%s' and the expected control result" \
                                    " do not match." % experimental_url)
                    return False, response_code
                else:
                    log.info("Fuzzy HTTP content comparison of experiment" \
                                 " URL '%s' and the expected control result" \
                                 " yielded a match." % experimental_url)
                    return True, response_code
            else:
                if str(response_content) != str(control_result):
                    log.info("HTTP content comparison of experiment URL" \
                                 " '%s' and the expected control result" \
                                 " do not match." % experimental_url)
                    return False, response_code
                else:
                    return True, response_code
        else:
            log.warn("HTTP connection appears to have failed.")
        return False, False
    
    def http_status_code_match(self, experiment_code, control_code):
        """
        Compare two HTTP status codes, returns True if they match.
        """
        if int(experiment_code) != int(control_code):
            return False
        return True

    def http_status_code_no_match(self, experiment_code, control_code):
        """
        Compare two HTTP status codes, returns True if they do not match.
        """
        if self.http_status_code_match(experiment_code, control_code):
            return False
        return True

    def run_vendor_tests(self, *a, **kw):
        """
        These are several vendor tests used to detect the presence of
        a captive portal. Each test compares HTTP status code and
        content to the control results and has its own User-Agent
        string, in order to emulate the test as it would occur on the
        device it was intended for. Vendor tests are defined in the
        format: 
        [exp_url, ctrl_result, ctrl_code, ua, test_name]
        """

        vendor_tests = [['http://www.apple.com/library/test/success.html',
                         'Success',
                         '200',
                         'Mozilla/5.0 (iPhone; U; CPU like Mac OS X; en) AppleWebKit/420+ (KHTML, like Gecko) Version/3.0 Mobile/1A543a Safari/419.3',
                         'Apple HTTP Captive Portal'],
                        ['http://tools.ietf.org/html/draft-nottingham-http-portal-02',
                         '428 Network Authentication Required',
                         '428',
                         'Mozilla/5.0 (Windows NT 6.1; rv:5.0) Gecko/20100101 Firefox/5.0',
                         'W3 Captive Portal'],
                        ['http://www.msftncsi.com/ncsi.txt',
                         'Microsoft NCSI',
                         '200',
                         'Microsoft NCSI',
                         'MS HTTP Captive Portal',]]

        cm = self.http_content_match_fuzzy_opt
        sm = self.http_status_code_match
        snm = self.http_status_code_no_match
        log = self.logger
        
        def compare_content(status_func, exp_url, ctrl_result, ctrl_code, headers, 
                            test_name, fuzzy):
            log.info("Running the %s test..." % test_name)
            content_match, exp_code = cm(exp_url, ctrl_result, headers, fuzzy)
            status_match = status_func(exp_code, ctrl_code)
            if status_match and content_match:
                log.info("The %s test was unable to detect a captive portal." % test_name)
            else:
                log.info("The %s test shows that your network is filtered." % test_name)

        for vt in vendor_tests:
            exp_url = vt[0]
            ctrl_result = vt[1]
            ctrl_code = vt[2]
            headers = {'User-Agent': vt[3]}
            test_name = vt[4]

            if test_name == "MS HTTP Captive Portal":
                fuzzy = False
                compare_content(sm, exp_url, ctrl_result, ctrl_code, headers, 
                                test_name, fuzzy)
                
            elif test_name == "Apple HTTP Captive Portal":
                fuzzy = True
                compare_content(sm, exp_url, ctrl_result, ctrl_code, headers, 
                                test_name, fuzzy)
                
            elif test_name == "W3 Captive Portal":
                fuzzy = True
                compare_content(snm, exp_url, ctrl_result, ctrl_code, headers, 
                                test_name, fuzzy)
                
            else:
                log.warn("Ooni is trying to run an undefined CP vendor test.")

    def experiment(self, *a, **kw):
        """
        Compares the content and status code of the HTTP response for
        experiment_url with the control_result and control_code 
        respectively. If the status codes match, but the experimental 
        content and control_result do not match, fuzzy matching is enabled
        to determine if the control_result is at least included somewhere
        in the experimental content. Returns True if matches are found,
        and False if otherwise.
        """
        if (os.path.isfile(os.path.join(self.config.main.assetdir,
                                        self.config.tests.captive_portal))):
            kw['data'].append(None)
            kw['data'].append('user defined')
        
        experiment_url = kw['data'][0]
        control_result = kw['data'][1]
        control_code = kw['data'][2]
        ua = kw['data'][3]
        test_name = kw['data'][4]
    
        cm = self.http_content_match_fuzzy_opt
        sm = self.http_status_code_match
        snm = self.http_status_code_no_match
        
        log = self.logger
        
        if test_name == "user defined":
            log.info("Running the %s test for %s..." % (test_name, experiment_url))
            content_match, experiment_code = cm(experiment_url, control_result)
            status_match = sm(experiment_code, control_code)
            if status_match and content_match:
                log.info("The %s test was unable to detect a captive portal." 
                         % test_name)
                return True, test_name
            elif status_match and not content_match:
                log.info("The %s test detected mismatched content, retrying "
                         "with fuzzy match enabled." % test_name)
                content_fuzzy_match, experiment_code = cm(experiment_url, 
                                                          control_result,
                                                          fuzzy=True)
                if content_fuzzy_match:
                    return True, test_name
                else:
                    return False, test_name
            else:
                log.info("The %s test shows that your network is filtered." 
                         % test_name)
                return False, test_name
        
        else:
            log.warn("Ooni is trying to run an undefined captive portal test.")
            return False, test_name
        

def run(ooni):
    """
    Runs the CaptivePortal(Test).

    If do_captive_portal_vendor_tests is set to true, then vendor
    specific captive portal tests will be run.

    If captive_portal = filename.txt, then user-specified tests
    will be run.

    Either vendor tests or user-defined tests can be run, or both.
    """
    config = ooni.config
    log = ooni.logger

    assets = []
    if (os.path.isfile(os.path.join(config.main.assetdir,
                                    config.tests.captive_portal))):
        assets.append(CaptivePortalAsset(os.path.join(config.main.assetdir, 
                                                      config.tests.captive_portal)))
    
    captiveportal = CaptivePortal(ooni)
    log.info("Starting captive portal test...")
    log.info("Running user defined tests...")
    captiveportal.run(assets, {'index': 1})
    
    if config.tests.do_captive_portal_vendor_tests:
        log.info("Running vendor tests...")
        captiveportal.run_vendor_tests()

    log.info("Captive portal test finished!")

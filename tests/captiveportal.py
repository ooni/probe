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

__plugoo__ = "captiveportal"
__desc__ = "Captive portal detection test"

class CaptivePortalAsset(Asset):
    """
    Parses captive_portal_test.txt into an Asset.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

    def parse_line(self, line):
        self = Asset.parse_line(self, line)
        return line.replace('\n', '').split(', ')

    '''
    def next_asset(self):
        self = Asset.next_asset(self)
        with self.fh as fh:
            asset_list = []
            lines = fh.readlines()
            for line in lines:
                parsed_line = self.parse_line(line)
                if parsed_line:
                    asset_list.append(parsed_line)
                else:
                    fh.seek(0)
                    raise StopIteration
            return asset_list
    '''

class CaptivePortal(Test):
    """
    Compares content and status codes of HTTP responses, and attempts
    to determine if content has been altered.

    TODO: compare headers
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
                                     fuzzy=False):
        """
        Makes an HTTP request on port 80 for experimental_url, then
        compares the response_content of experimental_url with the
        control_result. Optionally, if the fuzzy parameter is set to
        True, the response_content is compared with a regex of the
        control_result. If the response_content from the
        experimental_url and the control_result match, returns True
        with the HTTP status code, False if otherwise.
        """
        log = self.logger
        default_ua = self.default_ua

        response = self.http_fetch(experimental_url, 
                                   headers={'User-Agent': default_ua})
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
        test_name = kw['data'][0] 
        experiment_url = kw['data'][1]
        control_result = kw['data'][2]
        control_code = kw['data'][3]

        cm = self.http_content_match_fuzzy_opt
        sm = self.http_status_code_match

        log = self.logger
        log.info("Running the %s test..." % test_name)
        
        content_match, experiment_code = cm(experiment_url, control_result)
        status_match = sm(experiment_code, control_code)

        if status_match and content_match:
            log.info("The %s test was unable to detect a captive portal."
                     % test_name)
            return True
        elif status_match and not content_match:
            log.info("The %s test detected mismatched content, retrying with " \
                         "fuzzy match enabled." % test_name)
            content_fuzzy_match, experiment_code = cm(experiment_url, 
                                                      control_result,
                                                      fuzzy=True)
            if content_fuzzy_match:
                return True
            else:
                return False
        else:
            log.info("The %s test shows that your network is filtered, possibly " \
                         "due to a captive portal." % test_name)
            return False

        return False

def run(ooni):
    """
    Run the CaptivePortal(Test).
    """
    config = ooni.config
    log = ooni.logger
    assets = [CaptivePortalAsset(os.path.join(config.main.assetdir, 
                                              config.tests.captive_portal))]

    captiveportal = CaptivePortal(ooni)
    log.info("Starting captive portal test...")
    captiveportal.run(assets, {'index': 1})
    log.info("Captive portal test finished!")



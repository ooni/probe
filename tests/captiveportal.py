# -*- coding: utf-8 -*-
"""
    captiveportal
    *************

    This test is a collection of tests to detect the presence of a
    captive portal. Code is taken, in part, from the old ooni-probe,
    which was written by Jacob Appelbaum and Arturo Filastò.

    :copyright: (c) 2012 Isis Lovecruft
    :license: see LICENSE for more details
"""
import base64
import os
import re
import string
import urllib2
from urlparse import urlparse

from plugoo.assets import Asset
from plugoo.tests import Test

try:
    from dns import resolver
except ImportError:
    print "The dnspython module was not found. https://crate.io/packages/dnspython/"

try:
    from gevent import monkey
    monkey.patch_all(socket=True, dns=False, time=True, select=False, thread=True, 
                     os=True, ssl=True, httplib=False, aggressive=True)
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

    TODO: compare headers, compare 0x20 dns requests with authoritative
    server answers.
    """
    def __init__(self, ooni, name=__plugoo__):
        Test.__init__(self, ooni, name)
        self.default_ua = ooni.config.tests.default_ua

    def http_fetch(self, url, headers={}):
        """
        Parses an HTTP url, fetches it, and returns a urllib2 response
        object.
        """
        url = urlparse(url).geturl()
        request = urllib2.Request(url, None, headers)
        response = urllib2.urlopen(request)
        response_headers = dict(response.headers)
        return response, response_headers
 
    def http_content_match_fuzzy_opt(self, experimental_url, control_result,
                                     headers=None, fuzzy=False):
        """
        Makes an HTTP request on port 80 for experimental_url, then
        compares the response_content of experimental_url with the
        control_result. Optionally, if the fuzzy parameter is set to
        True, the response_content is compared with a regex of the
        control_result. If the response_content from the
        experimental_url and the control_result match, returns True
        with the HTTP status code and headers; False, status code, and
        headers if otherwise.
        """
        log = self.logger

        if headers is None:
            default_ua = self.default_ua
            headers = {'User-Agent': default_ua}

        response, response_headers = self.http_fetch(experimental_url, headers)
        response_content = response.read()
        response_code = response.code
        if response_content is not None:
            if fuzzy:
                pattern = re.compile(control_result)
                match = pattern.search(response_content)
                if not match:
                    log.info("Fuzzy HTTP content comparison for experiment URL")
                    log.info("'%s'" % experimental_url)
                    log.info("does not match!")
                    return False, response_code, response_headers
                else:
                    log.info("Fuzzy HTTP content comparison of experiment URL")
                    log.info("'%s'" % experimental_url)
                    log.info("and the expected control result yielded a match.")
                    return True, response_code, response_headers
            else:
                if str(response_content) != str(control_result):
                    log.info("HTTP content comparison of experiment URL")
                    log.info("'%s'" % experimental_url)
                    log.info("and the expected control result do not match.")
                    return False, response_code, response_headers
                else:
                    return True, response_code, response_headers
        else:
            log.warn("HTTP connection appears to have failed.")
        return False, False, False
    
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

    def dns_resolve(self, hostname, nameserver=None):
        """
        Resolves hostname though nameserver ns to its corresponding
        address(es). If ns is not given, use local DNS resolver.
        """
        log = self.logger

        if nameserver is not None:
            res = resolver.Resolver(configure=False)
            res.nameservers = [nameserver]
        else:
            res = resolver.Resolver()
        
        # This is gross and needs to be cleaned up, but it
        # was the best way I could find to handle all the
        # exceptions properly.
        try:
            answer = res.query(hostname)
            response = []
            for addr in answer:
                response.append(addr.address)
            return response
        except resolver.NoNameservers as nns:
            res.nameservers = ['8.8.8.8']
            try:
                answer = res.query(hostname)
                response = []
                for addr in answer:
                    response.append(addr.address)
                return response
            except resolver.NXDOMAIN as nx:
                log.info("DNS resolution for %s returned NXDOMAIN" % hostname)
                response = ['NXDOMAIN']
                return response
        except resolver.NXDOMAIN as nx:
            log.info("DNS resolution for %s returned NXDOMAIN" % hostname)
            response = ['NXDOMAIN']
            return response
        
    def dns_resolve_match(self, experiment_hostname, control_address):
        """
        Resolve experiment_hostname, and check to see that it returns
        an experiment_address which matches the control_address.  If
        they match, returns True and experiment_address; otherwise
        returns False and experiment_address.
        """
        log = self.logger

        experiment_address = self.dns_resolve(experiment_hostname)
        if experiment_address:
            if len(set(experiment_address) & set([control_address])) > 0:
                return True, experiment_address
            else:
                log.info("DNS comparison of control '%s' does not match " \
                             "experiment response '%s'" % control_address, address)
                return False, experiment_address
        else:
            log.debug("dns_resolve() for %s failed" % experiment_hostname)
            return None, experiment_address
            
    def get_random_url_safe_string(self, length):
        """
        Returns a random url-safe string of specified length, where 
        0 < length <= 256. The returned string will always start with 
        an alphabetic character.
        """
        if (length <= 0):
            length = 1
        elif (length > 256):
            length = 256

        random_ascii = base64.urlsafe_b64encode(os.urandom(int(length)))
        
        while not random_ascii[:1].isalpha():
            random_ascii = base64.urlsafe_b64encode(os.urandom(int(length)))

        three_quarters = int((len(random_ascii)) * (3.0/4.0))
        random_string = random_ascii[:three_quarters]
        return random_string

    def get_random_hostname(self, length=None):
        """
        Returns a random hostname with SLD of specified length. If
        length is unspecified, length=32 is used.

        These *should* all resolve to NXDOMAIN. If they actually
        resolve to a box that isn't part of a captive portal that
        would be rather interesting.
        """
        log = self.logger

        if length is None:
            length = 32
        
        random_sld = self.get_random_url_safe_string(length)

        # if it doesn't start with a letter, chuck it.
        while not random_sld[:1].isalpha():
            random_sld = self.get_random_url_safe_string(length)
        
        tld_list = ['.com', '.net', '.org', '.info', '.test', '.invalid']
        random_tld = urllib2.random.choice(tld_list)
        random_hostname = random_sld + random_tld
        return random_hostname

    def compare_random_hostnames(self, hostname_count=None, hostname_length=None):
        """
        Get hostname_count number of random hostnames with SLD length
        of hostname_length, and then attempt DNS resolution. If no
        arguments are given, default to three hostnames of 32 bytes
        each. These random hostnames *should* resolve to NXDOMAIN,
        except in the case where a user is presented with a captive
        portal and remains unauthenticated, in which case the captive
        portal may return the address of the authentication page.

        If the cardinality of the intersection of the set of resolved
        random hostnames and the single element control set
        (['NXDOMAIN']) are equal to one, then DNS properly resolved.

        Returns true if only NXDOMAINs were returned, otherwise returns
        False with the relative complement of the control set in the
        response set.
        """
        log = self.logger

        if hostname_count is None:
            hostname_count = 3
        
        log.info("Generating random hostnames...")
        log.info("Resolving DNS for %d random hostnames..." % hostname_count)

        control = ['NXDOMAIN']
        responses = []

        for x in range(hostname_count):
            random_hostname = self.get_random_hostname(hostname_length)
            response_match, response_address = self.dns_resolve_match(random_hostname,
                                                                      control[0])
            for address in response_address:
                if response_match is False:
                    log.info("Strangely, DNS resolution of the random hostname")
                    log.info("%s actually points to %s" 
                             % (random_hostname, response_address))
                    responses = responses + [address]
                else:
                    responses = responses + [address]

        intersection = set(responses) & set(control)
        relative_complement = set(responses) - set(control)
        r = set(responses)
        
        if len(intersection) == 1:
            log.info("All %d random hostnames properly resolved to NXDOMAIN." 
                     % hostname_count)
            return True, relative_complement
        elif (len(intersection) == 1) and (len(r) > 1):
            log.info("Something odd happened. Some random hostnames correctly")
            log.info("resolved to NXDOMAIN, but several others resolved to")
            log.info("to the following addresses: %s" % relative_complement)
            return False, relative_complement
        elif (len(intersection) == 0) and (len(r) == 1):
            log.info("All random hostnames resolved to the IP address ")
            log.info("'%s', which is indicative of a captive portal." % r)
            return False, relative_complement
        else:
            log.debug("Apparently, pigs are flying on your network, 'cause a")
            log.debug("bunch of hostnames made from 32-byte random strings")
            log.debug("just magically resolved to a bunch of random addresses.")
            log.debug("That is definitely highly improbable. In fact, my napkin")
            log.debug("tells me that the probability of just one of those")
            log.degug("hostnames resolving to an address is 1.68e-59, making")
            log.debug("it nearly twice as unlikely as an MD5 hash collision.")
            log.debug("Either someone is seriously messing with your network,")
            log.debug("or else you are witnessing the impossible. %s" % r)
            return False, relative_complement

    def google_dns_cp_test(self):
        """
        Google Chrome resolves three 10-byte random hostnames.
        """
        log = self.logger
        subtest = "Google Chrome DNS-based"

        log.info("")
        log.info("Running the Google Chrome DNS-based captive portal test...")

        gmatch, google_dns_result = self.compare_random_hostnames(3, 10)

        if gmatch:
            log.info("Google Chrome DNS-based captive portal test did not")
            log.info("detect a captive portal.")
            return google_dns_result
        else:
            log.info("Google Chrome DNS-based captive portal test believes")
            log.info("you are in a captive portal, or else something very")
            log.info("odd is happening with your DNS.")
            return google_dns_result
        
    def ms_dns_cp_test(self):
        """
        Microsoft "phones home" to a server which will always resolve 
        to the same address.
        """
        log = self.logger
        subtest = "Microsoft NCSI DNS-based"

        log.info("")
        log.info("Running the Microsoft NCSI DNS-based captive portal")
        log.info("test...")

        msmatch, ms_dns_result = self.dns_resolve_match("dns.msftncsi.com", 
                                                        "131.107.255.255")
        if msmatch:
            log.info("Microsoft NCSI DNS-based captive portal test did not")
            log.info("detect a captive portal.")
            return ms_dns_result
        else:
            log.info("Microsoft NCSI DNS-based captive portal test ")
            log.info("believes you are in a captive portal.")
            return ms_dns_result
    
    def run_vendor_dns_tests(self):
        """
        Run the vendor DNS tests.
        """
        self.google_dns_cp_test()
        self.ms_dns_cp_test()

        return

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
        
        def compare_content(status_func, fuzzy, experiment_url, control_result, 
                            control_code, headers, test_name):
            log.info("")
            log.info("Running the %s test..." % test_name)

            content_match, experiment_code, experiment_headers = cm(experiment_url, 
                                                                    control_result, 
                                                                    headers, fuzzy)
            status_match = status_func(experiment_code, control_code)

            if status_match and content_match:
                log.info("The %s test was unable to detect" % test_name)
                log.info("a captive portal.")
            else:
                log.info("The %s test shows that your network" % test_name)
                log.info("is filtered.")

        for vt in vendor_tests:
            experiment_url = vt[0]
            control_result = vt[1]
            control_code = vt[2]
            headers = {'User-Agent': vt[3]}
            test_name = vt[4]

            args = (experiment_url, control_result, control_code, headers, test_name)

            if test_name == "MS HTTP Captive Portal":
                compare_content(sm, False, *args)
                
            elif test_name == "Apple HTTP Captive Portal":
                compare_content(sm, True, *args)
                
            elif test_name == "W3 Captive Portal":
                compare_content(snm, True, *args)
                
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
            kw['data'].append('user-defined')
        
        experiment_url = kw['data'][0]
        control_result = kw['data'][1]
        control_code = kw['data'][2]
        ua = kw['data'][3]
        test_name = kw['data'][4]
    
        cm = self.http_content_match_fuzzy_opt
        sm = self.http_status_code_match
        snm = self.http_status_code_no_match
        
        log = self.logger
        
        if test_name == "user-defined":
            log.info("Running %s test for '%s'..." % (test_name, experiment_url))
            content_match, experiment_code, experiment_headers = cm(experiment_url, 
                                                                    control_result)
            status_match = sm(experiment_code, control_code)
            if status_match and content_match:
                log.info("The %s test for '%s'" % (test_name, experiment_url))
                log.info("was unable to detect a captive portal.")
                return True, test_name
            elif status_match and not content_match:
                log.info("Retrying '%s' with fuzzy match enabled."
                         % experiment_url)
                fuzzy_match, experiment_code, experiment_headers = cm(experiment_url, 
                                                                      control_result,
                                                                      fuzzy=True)
                if fuzzy_match:
                    return True, test_name
                else:
                    log.info("Found modified content on '%s'," % experiment_url)
                    log.info("which could indicate a captive portal.")
                    
                    return False, test_name
            else:
                log.info("The content comparison test for ")
                log.info("'%s'" % experiment_url)
                log.info("shows that your HTTP traffic is filtered.")
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
    tally = ooni.tally

    assets = []
    if (os.path.isfile(os.path.join(config.main.assetdir,
                                    config.tests.captive_portal))):
        assets.append(CaptivePortalAsset(os.path.join(config.main.assetdir, 
                                                      config.tests.captive_portal)))
    
    captiveportal = CaptivePortal(ooni)
    log.info("Starting captive portal test...")
    captiveportal.run(assets, {'index': 1, 'tally': tally.count, 
                               'tally_marks': tally.marks})
    
    if config.tests.do_captive_portal_vendor_tests:
        log.info("")
        log.info("Running vendor tests...")
        captiveportal.run_vendor_tests()

    if config.tests.do_captive_portal_vendor_dns_tests:
        log.info("")
        log.info("Running vendor DNS-based tests...")
        captiveportal.run_vendor_dns_tests()

    log.info("Captive portal test finished!")

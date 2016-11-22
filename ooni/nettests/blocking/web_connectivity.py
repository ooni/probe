# -*- encoding: utf-8 -*-

import csv
from urlparse import urlparse

from ipaddr import IPv4Address, AddressValueError

from twisted.web.client import GzipDecoder
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.names import client

from twisted.internet import defer
from twisted.python import usage

from ooni import geoip
from ooni.utils import log

from ooni.backend_client import WebConnectivityClient

from ooni.common.http_utils import extractTitle
from ooni.utils.net import COMMON_SERVER_HEADERS
from ooni.templates import httpt, dnst
from ooni.errors import failureToString

from ooni.common.tcp_utils import TCPConnectFactory
from ooni.common.http_utils import REQUEST_HEADERS

class InvalidControlResponse(Exception):
    pass

class AbsentHostname(Exception):
    pass

class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test'],
        ['dns-discovery', 'd', 'whoami.akamai.net', 'Specify the dns discovery test helper'],
        ['backend', 'b', None, 'The web_consistency backend test helper'],
        ['retries', 'r', 1, 'Number of retries for the HTTP request'],
        ['timeout', 't', 240, 'Total timeout for this test'],
    ]


def is_public_ipv4_address(address):
    try:
        ip_address = IPv4Address(address)
        return not any(
            [ip_address.is_private, ip_address.is_loopback]
        )
    except AddressValueError:
        return None

class WebConnectivityTest(httpt.HTTPTest, dnst.DNSTest):
    """
    Web connectivity
    """
    name = "Web connectivity"
    description = ("Identifies the reason for blocking of a given URL by "
                   "performing DNS resolution of the hostname, doing a TCP "
                   "connect to the resolved IPs and then fetching the page "
                   "and comparing all these results with those of a control.")
    author = "Arturo Filastò"
    version = "0.1.0"

    contentDecoders = [('gzip', GzipDecoder)]

    usageOptions = UsageOptions

    inputFile = [
        'file', 'f', None, 'List of URLS to perform GET requests to'
    ]

    requiredTestHelpers = {
        'backend': 'web-connectivity',
        'dns-discovery': 'dns-discovery'
    }
    requiredOptions = ['backend', 'dns-discovery']
    requiresRoot = False
    requiresTor = False
    followRedirects = True

    # These are the options to be shown on the GUI
    simpleOptions = [
        {"name": "url", "type": "text"},
        {"name": "file", "type": "file/url"}
    ]

    # Factor used to determine HTTP blockpage detection
    # the factor 0.7 comes from http://www3.cs.stonybrook.edu/~phillipa/papers/JLFG14.pdf
    factor = 0.7
    resolverIp = None

    @classmethod
    @defer.inlineCallbacks
    def setUpClass(cls):
        try:
            answers = yield client.lookupAddress(
                cls.localOptions['dns-discovery']
            )
            assert len(answers) > 0
            assert len(answers[0]) > 0
            cls.resolverIp = answers[0][0].payload.dottedQuad()
        except Exception as exc:
            log.exception(exc)
            log.err("Failed to lookup the resolver IP address")


    def inputProcessor(self, filename):
        """
        This is a specialised inputProcessor that also supports taking as
        input a csv file.
        """
        def csv_generator(fh):
            for row in csv.reader(fh):
                yield row[0]

        def simple_file_generator(fh):
            for line in fh:
                l = line.strip()
                # Skip empty lines
                if not l:
                    continue
                # Skip comment lines
                if l.startswith('#'):
                    continue
                yield l

        fh = open(filename)
        try:
            line = fh.readline()
            # Detect the line of the citizenlab input file
            if line.startswith("url,"):
                generator = csv_generator(fh)
            else:
                fh.seek(0)
                generator = simple_file_generator(fh)
            for i in generator:
                if (not i.startswith("http://") and
                        not i.startswith("https://")):
                    i = "http://{}/".format(i)
                yield i
        finally:
            fh.close()

    def setUp(self):
        """
        Check for inputs.
        """
        if self.localOptions['url']:
            self.input = self.localOptions['url']
        if not self.input:
            raise Exception("No input specified")

        try:
            self.localOptions['retries'] = int(self.localOptions['retries'])
        except ValueError:
            self.localOptions['retries'] = 2

        self.timeout = int(self.localOptions['timeout'])

        self.report['retries'] = self.localOptions['retries']
        self.report['client_resolver'] = self.resolverIp
        self.report['dns_consistency'] = None
        self.report['body_length_match'] = None
        self.report['headers_match'] = None
        self.report['status_code_match'] = None

        self.report['accessible'] = None
        self.report['blocking'] = None

        self.report['control_failure'] = None
        self.report['http_experiment_failure'] = None
        self.report['dns_experiment_failure'] = None

        self.report['tcp_connect'] = []
        self.report['control'] = {}

        self.hostname = urlparse(self.input).netloc
        if not self.hostname:
            raise AbsentHostname('No hostname', self.input)

        self.control = {
            'tcp_connect': {},
            'dns': {
                'addrs': [],
                'failure': None,
            },
            'http_request': {
                'body_length': -1,
                'failure': None,
                'status_code': -1,
                'headers': {},
                'title': ''
            }
        }
        if isinstance(self.localOptions['backend'], dict):
            self.web_connectivity_client = WebConnectivityClient(
                settings=self.localOptions['backend']
            )
        else:
            self.web_connectivity_client = WebConnectivityClient(
                self.localOptions['backend']
            )

    def experiment_dns_query(self):
        log.msg("* doing DNS query for {}".format(self.hostname))
        return self.performALookup(self.hostname)

    def experiment_tcp_connect(self, socket):
        log.msg("* connecting to {}".format(socket))
        ip_address, port = socket.split(":")
        port = int(port)
        result = {
            'ip': ip_address,
            'port': port,
            'status': {
                'success': None,
                'failure': None,
                'blocked': None
            }
        }
        point = TCP4ClientEndpoint(reactor, ip_address, port)
        d = point.connect(TCPConnectFactory())
        @d.addCallback
        def cb(p):
            result['status']['success'] = True
            result['status']['blocked'] = False
            self.report['tcp_connect'].append(result)

        @d.addErrback
        def eb(failure):
            result['status']['success'] = False
            result['status']['failure'] = failureToString(failure)
            self.report['tcp_connect'].append(result)

        return d

    @defer.inlineCallbacks
    def control_request(self, sockets):
        log.msg("* performing control request with backend")
        self.control = yield self.web_connectivity_client.control(
            http_request=self.input,
            tcp_connect=sockets
        )
        self.report['control'] = self.control

    @defer.inlineCallbacks
    def experiment_http_get_request(self):
        log.msg("* doing HTTP(s) request {}".format(self.input))
        retries = 0
        while True:
            try:
                result = yield self.doRequest(self.input,
                                              headers=REQUEST_HEADERS)
                break
            except:
                if retries > self.localOptions['retries']:
                    log.debug("Finished all the allowed retries")
                    raise
                log.debug("Re-running HTTP request")
                retries += 1

        defer.returnValue(result)

    def compare_headers(self, experiment_http_response):
        control_headers_lower = {k.lower(): v for k, v in
                self.report['control']['http_request']['headers'].items()
        }
        experiment_headers_lower = {k.lower(): v for k, v in
            experiment_http_response.headers.getAllRawHeaders()
        }

        if (set(control_headers_lower.keys()) ==
                set(experiment_headers_lower.keys())):
            return True

        uncommon_ctrl_headers = (set(control_headers_lower.keys()) -
                                 set(COMMON_SERVER_HEADERS))
        uncommon_exp_headers = (set(experiment_headers_lower.keys()) -
                                set(COMMON_SERVER_HEADERS))

        return len(uncommon_ctrl_headers.intersection(
                            uncommon_exp_headers)) > 0

    def compare_body_lengths(self, experiment_http_response):
        control_body_length = self.control['http_request']['body_length']
        experiment_body_length = len(experiment_http_response.body)

        if control_body_length == experiment_body_length:
            rel = float(1)
        elif control_body_length == 0 or experiment_body_length == 0:
            rel = float(0)
        else:
            rel = float(control_body_length) / float(experiment_body_length)

        if rel > 1:
            rel = 1/rel

        self.report['body_proportion'] = rel
        if rel > float(self.factor):
            return True
        else:
            return False

    def compare_titles(self, experiment_http_response):
        experiment_title = extractTitle(experiment_http_response.body).strip()
        control_title = self.control['http_request']['title'].strip()

        control_words = control_title.split(' ')
        for idx, exp_word in enumerate(experiment_title.split(' ')):
            # We don't consider to match words that are shorter than 5
            # characters (5 is the average word length for english)
            if len(exp_word) < 5:
                continue
            try:
                return control_words[idx].lower() == exp_word.lower()
            except IndexError:
                return False

    def compare_http_experiments(self, experiment_http_response):

        self.report['body_length_match'] = \
            self.compare_body_lengths(experiment_http_response)

        self.report['headers_match'] = \
            self.compare_headers(experiment_http_response)

        if str(self.control['http_request']['status_code'])[0] != '5':
            self.report['status_code_match'] =  (
                self.control['http_request']['status_code'] ==
                experiment_http_response.code
            )

        self.report['title_match'] = self.compare_titles(experiment_http_response)

    def compare_dns_experiments(self, experiment_dns_answers):
        if self.control['dns']['failure'] is not None and \
                self.control['dns']['failure'] == self.report['dns_experiment_failure']:
            self.report['dns_consistency'] = 'consistent'
            return True

        control_addrs = set(self.control['dns']['addrs'])
        experiment_addrs = set(experiment_dns_answers)

        if control_addrs == experiment_addrs:
            return True

        for experiment_addr in experiment_addrs:
            if is_public_ipv4_address(experiment_addr) is False:
                return False

        if len(control_addrs.intersection(experiment_addrs)) > 0:
            return True

        experiment_asns = set(map(lambda x: geoip.ip_to_location(x)['asn'],
                                  experiment_addrs))
        control_asns = set(map(lambda x: geoip.ip_to_location(x)['asn'],
                               control_addrs))

        # Remove the instance of AS0 when we fail to find the ASN
        control_asns.discard('AS0')
        experiment_asns.discard('AS0')

        if len(control_asns.intersection(experiment_asns)) > 0:
            return True

        return False

    def compare_tcp_experiments(self):
        success = True
        for idx, result in enumerate(self.report['tcp_connect']):
            socket = "%s:%s" % (result['ip'], result['port'])
            control_status = self.control['tcp_connect'][socket]
            if result['status']['success'] == False and \
                    control_status['status'] == True:
                self.report['tcp_connect'][idx]['status']['blocked'] = True
                success = False
            else:
                self.report['tcp_connect'][idx]['status']['blocked'] = False
        return success

    def determine_blocking(self, experiment_http_response, experiment_dns_answers):
        blocking = False

        control_http_failure = self.control['http_request']['failure']
        if control_http_failure is not None:
            control_http_failure = control_http_failure.split(" ")[0]

        experiment_http_failure = self.report['http_experiment_failure']
        if experiment_http_failure is not None:
            experiment_http_failure = experiment_http_failure.split(" ")[0]

        if (experiment_http_failure is None and control_http_failure is None):
            self.compare_http_experiments(experiment_http_response)

        dns_consistent = self.compare_dns_experiments(experiment_dns_answers)
        if dns_consistent is True:
            self.report['dns_consistency'] = 'consistent'
        else:
            self.report['dns_consistency'] = 'inconsistent'
        tcp_connect = self.compare_tcp_experiments()

        got_expected_web_page = None
        if (experiment_http_failure is None and
                    control_http_failure is None):
            got_expected_web_page = (
                (self.report['body_length_match'] is True or
                 self.report['headers_match'] is True or
                 self.report['title_match'] is True)
                and self.report['status_code_match'] is not False
            )

        if (dns_consistent == True and tcp_connect == False and
                experiment_http_failure is not None):
            blocking = 'tcp_ip'

        elif (dns_consistent == True and
              tcp_connect == True and
              got_expected_web_page == False):
            blocking = 'http-diff'

        elif (dns_consistent == True and
              tcp_connect == True and
              experiment_http_failure is not None and
              control_http_failure is None):
            if experiment_http_failure == 'dns_lookup_error':
                blocking = 'dns'
            else:
                blocking = 'http-failure'

        elif (dns_consistent == False and
                  (got_expected_web_page == False or
                    experiment_http_failure is not None)):
            blocking = 'dns'

        # This happens when the DNS resolution is injected, but the domain
        # doesn't have a valid record anymore or it resolves to an address
        # that is only accessible from within the country/network of the probe.
        elif (dns_consistent == False and
              got_expected_web_page == False and
                  (self.control['dns']['failure'] is not None or
                   control_http_failure != experiment_http_failure)):
            blocking = 'dns'

        return blocking


    @defer.inlineCallbacks
    def test_web_connectivity(self):
        log.msg("")
        log.msg("Starting test for {}".format(self.input))
        experiment_dns = self.experiment_dns_query()

        @experiment_dns.addErrback
        def dns_experiment_err(failure):
            self.report['dns_experiment_failure'] = failureToString(failure)
            return []
        experiment_dns_answers = yield experiment_dns

        port = 80
        parsed_url = urlparse(self.input)
        if parsed_url.port:
            port = parsed_url.port
        elif parsed_url.scheme == 'https':
            port = 443

        sockets = []
        for ip_address in experiment_dns_answers:
            if is_public_ipv4_address(ip_address) is True:
                sockets.append("{}:{}".format(ip_address, port))

        # STEALTH in here we should make changes to make the test more stealth
        dl = []
        for socket in sockets:
            dl.append(self.experiment_tcp_connect(socket))
        results = yield defer.DeferredList(dl)

        experiment_http = self.experiment_http_get_request()
        @experiment_http.addErrback
        def http_experiment_err(failure):
            failure_string = failureToString(failure)
            log.err("Failed to perform HTTP request %s" % failure_string)
            self.report['http_experiment_failure'] = failure_string

        experiment_http_response = yield experiment_http

        control_request = self.control_request(sockets)
        @control_request.addErrback
        def control_err(failure):
            failure_string = failureToString(failure)
            log.err("Failed to perform control lookup: %s" % failure_string)
            self.report['control_failure'] = failure_string

        yield control_request

        if self.report['control_failure'] is None:
            self.report['blocking'] = self.determine_blocking(experiment_http_response, experiment_dns_answers)

        log.msg("")
        log.msg("Result for %s" % self.input)
        log.msg("-----------" + "-"*len(self.input))

        if self.report['blocking'] is None:
            log.msg("* Could not determine status of blocking due to "
                    "failing control request")
        elif self.report['blocking'] is False:
            log.msg("* No blocking detected")
        else:
            log.msg("* BLOCKING DETECTED due to %s" % (self.report['blocking']))

        if (self.report['http_experiment_failure'] == None and
                self.report['dns_experiment_failure'] == None and
                self.report['blocking'] in (False, None)):
            self.report['accessible'] = True
            log.msg("* Is accessible")
        else:
            log.msg("* Is NOT accessible")
            self.report['accessible'] = False
        log.msg("")

    def postProcessor(self, measurements):
        self.summary['accessible'] = self.summary.get('accessible', [])
        self.summary['not-accessible'] = self.summary.get('not-accessible', [])
        self.summary['blocked'] = self.summary.get('blocked', {})

        if self.report['blocking'] not in (False, None):
            self.summary['blocked'][self.report['blocking']] = \
                self.summary['blocked'].get(self.report['blocking'], [])

            self.summary['blocked'][self.report['blocking']].append(
                self.input)

        if self.report['accessible'] is True:
            self.summary['accessible'].append(self.input)
        else:
            self.summary['not-accessible'].append(self.input)
        return self.report

    def displaySummary(self, summary):

        if len(summary['accessible']) > 0:
            log.msg("")
            log.msg("Accessible URLS")
            log.msg("---------------")
            for url in summary['accessible']:
                log.msg("* {}".format(url))

        if len(summary['not-accessible']) > 0:
            log.msg("")
            log.msg("Not accessible URLS")
            log.msg("-------------------")
            for url in summary['not-accessible']:
                log.msg("* {}".format(url))

        if len(summary['blocked']) > 0:

            for reason, urls in summary['blocked'].items():
                log.msg("")
                log.msg("URLS possibly blocked due to {}".format(reason))
                log.msg("-----------------------------"+'-'*len(reason))
                for url in urls:
                    log.msg("* {}".format(url))

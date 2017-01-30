# -*- encoding: utf-8 -*-

import csv
from urlparse import urlparse

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.names import client
from twisted.python import usage
from twisted.web.client import GzipDecoder

from ooni import geoip
from ooni.backend_client import WebConnectivityClient
from ooni.common.http_utils import REQUEST_HEADERS
from ooni.common.http_utils import extractTitle
from ooni.common.ip_utils import is_public_ipv4_address
from ooni.common.tcp_utils import TCPConnectFactory
from ooni.errors import failureToString
from ooni.templates import httpt, dnst
from ooni.utils import log
from ooni.utils.net import COMMON_SERVER_HEADERS
from ooni import libmk


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
    ignorePrivateRedirects = True

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

    @defer.inlineCallbacks
    def test_web_connectivity(self):
        log.msg("")
        log.msg("Starting test for {}".format(self.input))

        test_keys = yield libmk.web_connectivity(9876, 'antani', self.input, {
            "nameserver": "8.8.8.8:53", # XXX
            "dns/resolver": "system",
            "backend": self.localOptions['backend']['address']
        })
        self.report = test_keys

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

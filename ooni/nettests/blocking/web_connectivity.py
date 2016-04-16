# -*- encoding: utf-8 -*-

import json
from urlparse import urlparse

from ipaddr import IPv4Address, AddressValueError

from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.names import client, dns

from twisted.internet import defer
from twisted.python import usage

from ooni import geoip
from ooni.utils import log

from ooni.utils.net import StringProducer, BodyReceiver
from ooni.templates import httpt, dnst
from ooni.errors import failureToString

REQUEST_HEADERS = {
    'User-Agent': ['Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, '
                   'like Gecko) Chrome/47.0.2526.106 Safari/537.36'],
    'Accept-Language': ['en-US;q=0.8,en;q=0.5'],
    'Accept': ['text/html,application/xhtml+xml,application/xml;q=0.9,'
               '*/*;q=0.8']
}

class InvalidControlResponse(Exception):
    pass

class TCPConnectProtocol(Protocol):
    def connectionMade(self):
        self.transport.loseConnection()

class TCPConnectFactory(Factory):
    noisy = False
    def buildProtocol(self, addr):
        return TCPConnectProtocol()


class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test'],
        ['dns-discovery', 'd', 'whoami.akamai.net', 'Specify the dns discovery test helper'],
        ['backend', 'b', None, 'The web_consistency backend test helper'],
    ]


def is_public_ipv4_address(address):
    try:
        ip_address = IPv4Address(address)
        if not any([ip_address.is_private,
                    ip_address.is_loopback]):
            return True
        return False
    except AddressValueError:
        return None

class WebConnectivityTest(httpt.HTTPTest, dnst.DNSTest):
    """
    Web connectivity
    """
    name = "Web connectivity"
    description = ("Performs a HTTP GET request over Tor and one over the "
                  "local network and compares the two results.")
    author = "Arturo Filastò"
    version = "0.1.0"

    usageOptions = UsageOptions

    inputFile = [
        'file', 'f', None, 'List of URLS to perform GET requests to'
    ]

    requiredTestHelpers = {
        'backend': 'web-connectivity',
        'dns-discovery': 'dns-discovery'
    }
    requiresRoot = False
    requiresTor = False
    followRedirects = True

    # Factor used to determine HTTP blockpage detection
    factor = 0.8
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

    def setUp(self):
        """
        Check for inputs.
        """
        if self.localOptions['url']:
            self.input = self.localOptions['url']
        if not self.input:
            raise Exception("No input specified")

        self.report['client_resolver'] = self.resolverIp
        self.report['dns_consistency'] = None
        self.report['body_length_match'] = None
        self.report['headers_match'] = None

        self.report['accessible'] = None
        self.report['blocking'] = None

        self.report['control_failure'] = None
        self.report['http_experiment_failure'] = None
        self.report['dns_experiment_failure'] = None

        self.report['tcp_connect'] = []
        self.report['control'] = {}

        self.hostname = urlparse(self.input).netloc
        if not self.hostname:
            raise Exception("Invalid input")

        self.control = {
            'tcp_connect': {},
            'dns': {
                'ips': []
            },
            'http_request': {
                'body_length': None,
                'failure': True,
                'headers': {}
            }
        }

    def experiment_dns_query(self):
        log.msg("Doing DNS query for {}".format(self.hostname))
        return self.performALookup(self.hostname)

    def tcp_connect(self, socket):
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
        bodyProducer = StringProducer(json.dumps({
            'http_request': self.input,
            'tcp_connect': sockets
        }))
        response = yield self.agent.request("POST",
                                            str(self.localOptions['backend']),
                                            bodyProducer=bodyProducer)
        try:
            content_length = int(response.headers.getRawHeaders('content-length')[0])
        except Exception:
            content_length = None

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished, content_length))
        body = yield finished
        try:
            self.control = json.loads(body)
            assert 'http_request' in self.control.keys()
            assert 'tcp_connect' in self.control.keys()
            assert 'dns' in self.control.keys()
        except AssertionError, ValueError:
            raise InvalidControlResponse(body)
        self.report['control'] = self.control

    def experiment_http_get_request(self):
        return self.doRequest(self.input, headers=REQUEST_HEADERS)

    def compare_headers(self, experiment_http_response):
        count = 0
        control_headers_lower = {k.lower(): v for k, v in
                self.report['control']['http_request']['headers'].items()}

        for header_name, header_value in \
                experiment_http_response.headers.getAllRawHeaders():
            try:
                control_headers_lower[header_name.lower()]
            except KeyError:
                log.msg("Did not find the key {}".format(header_name))
                return False
            count += 1

        return count == len(self.report['control']['http_request']['headers'])

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

    def compare_dns_experiments(self, experiment_dns_answers):
        if self.control['dns']['failure'] is not None and \
                self.control['dns']['failure'] == self.report['dns_experiment_failure']:
            self.report['dns_consistency'] = 'consistent'
            return True

        control_ips = set(self.control['dns']['ips'])
        experiment_ips = set(experiment_dns_answers)

        if control_ips == experiment_ips:
            return True

        for experiment_ip in experiment_ips:
            if is_public_ipv4_address(experiment_ip) is False:
                return False

        if len(control_ips.intersection(experiment_ips)) > 0:
            return True

        experiment_asns = set(map(lambda x: geoip.IPToLocation(x)['asn'],
                              experiment_ips))
        control_asns = set(map(lambda x: geoip.IPToLocation(x)['asn'],
                           control_ips))

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

        if (self.report['http_experiment_failure'] is None and
                    self.report['control']['http_request']['failure'] is None):
            self.report['body_length_match'] = self.compare_body_lengths(
                experiment_http_response)
            self.report['headers_match'] = self.compare_headers(
                experiment_http_response)

        dns_consistent = self.compare_dns_experiments(experiment_dns_answers)
        if dns_consistent is True:
            self.report['dns_consistency'] = 'consistent'
        else:
            self.report['dns_consistency'] = 'inconsistent'
        tcp_connect = self.compare_tcp_experiments()

        if dns_consistent == True and tcp_connect == False:
            blocking = 'tcp_ip'

        elif (dns_consistent == True and tcp_connect == True and
                      self.report['body_length_match'] == False):
            blocking = 'http'

        elif dns_consistent == False:
            blocking = 'dns'

        return blocking


    @defer.inlineCallbacks
    def test_web_connectivity(self):
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
            dl.append(self.tcp_connect(socket))
        results = yield defer.DeferredList(dl)

        experiment_http = self.experiment_http_get_request()
        @experiment_http.addErrback
        def http_experiment_err(failure):
            self.report['http_experiment_failure'] = failureToString(failure)

        experiment_http_response = yield experiment_http

        control_request = self.control_request(sockets)
        @control_request.addErrback
        def control_err(failure):
            log.err("Failed to perform control lookup")
            self.report['control_failure'] = failureToString(failure)

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

    def postProcessor(self, measurements):
        self.summary['accessible'] = self.summary.get('accessible', [])
        self.summary['not-accessible'] = self.summary.get('not-accessible', [])
        self.summary['blocked'] = self.summary.get('blocked', [])

        if self.report['blocking'] not in (False, None):
            self.summary['blocked'].append((self.input,
                                            self.report['blocking']))
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
            log.msg("---------------")
            for url in summary['not-accessible']:
                log.msg("* {}".format(url))

        if len(summary['blocked']) > 0:
            log.msg("")
            log.msg("Blocked URLS")
            log.msg("------------")
            for url, reason in summary['blocked']:
                log.msg("* {} due to {}".format(url, reason))

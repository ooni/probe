# -*- encoding: utf-8 -*-

import json
from urlparse import urlparse

from ipaddr import IPv4Address, AddressValueError

from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

from twisted.internet import defer
from twisted.python import usage

from ooni import geoip
from ooni.utils import log

from ooni.utils.net import StringProducer, BodyReceiver
from ooni.templates import httpt, dnst
from ooni.errors import failureToString

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
        ['dns-discovery', 'd', None, 'Specify the dns discovery test helper'],
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

    # Factor used to determine HTTP blockpage detection
    factor = 0.8

    def setUp(self):
        """
        Check for inputs.
        """
        if self.localOptions['url']:
            self.input = self.localOptions['url']
        if not self.input:
            raise Exception("No input specified")

        self.report['client_resolver'] = None
        self.report['dns_consistency'] = None
        self.report['body_length_match'] = None
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

    def dns_discovery(self):
        return self.performALookup(self.localOptions['dns-discovery'])

    def experiment_dns_query(self):
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
        self.control = json.loads(body)
        self.report['control'] = self.control

    def experiment_http_get_request(self):
        return self.doRequest(self.input)

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
            self.report['body_length_match'] = True
            return True
        else:
            self.report['body_length_match'] = False
            return False

    def compare_dns_experiments(self, experiment_dns_answers):
        if self.control['dns']['failure'] is not None and \
                self.control['dns']['failure'] == self.report['dns_experiment_failure']:
            self.report['dns_consistency'] = 'consistent'
            return True

        control_ips = set(self.control['dns']['ips'])
        experiment_ips = set(experiment_dns_answers)

        for experiment_ip in experiment_ips:
            if is_public_ipv4_address(experiment_ip) is False:
                self.report['dns_consistency'] = 'inconsistent'
                return False

        if len(control_ips.intersection(experiment_ips)) > 0:
            self.report['dns_consistency'] = 'consistent'
            return True

        experiment_asns = set(map(lambda x: geoip.IPToLocation(x)['asn'],
                              experiment_ips))
        control_asns = set(map(lambda x: geoip.IPToLocation(x)['asn'],
                           control_ips))

        if len(control_asns.intersection(experiment_asns)) > 0:
            self.report['dns_consistency'] = 'consistent'
            return True

        self.report['dns_consistency'] = 'inconsistent'
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
        blocking = None
        body_length_match = None
        dns_consistent = None
        tcp_connect = None

        if self.report['control_failure'] is None and \
                self.report['http_experiment_failure'] is None and \
                self.report['control']['http_request']['failure'] is None:
            body_length_match = self.compare_body_lengths(experiment_http_response)

        if self.report['control_failure'] is None:
            dns_consistent = self.compare_dns_experiments(experiment_dns_answers)

        if self.report['control_failure'] is None:
            tcp_connect = self.compare_tcp_experiments()

        if dns_consistent == True and tcp_connect == False:
            blocking = 'tcp_ip'

        elif dns_consistent == True and \
                tcp_connect == True and body_length_match == False:
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

        results = yield defer.DeferredList([
            self.dns_discovery(),
            experiment_dns
        ])

        self.report['client_resolver'] = None
        if results[0][0] == True:
            self.report['client_resolver']  = results[0][1][1]

        experiment_dns_answers = results[1][1]
        sockets = []
        for answer in experiment_dns_answers:
            if is_public_ipv4_address(answer) is True:
                sockets.append("%s:80" % answer)

        control_request = self.control_request(sockets)
        @control_request.addErrback
        def control_err(failure):
            self.report['control_failure'] = failureToString(failure)

        dl = [control_request]
        for socket in sockets:
            dl.append(self.tcp_connect(socket))
        results = yield defer.DeferredList(dl)

        experiment_http = self.experiment_http_get_request()
        @experiment_http.addErrback
        def http_experiment_err(failure):
            self.report['http_experiment_failure'] = failureToString(failure)

        experiment_http_response = yield experiment_http

        blocking = self.determine_blocking(experiment_http_response, experiment_dns_answers)
        self.report['blocking'] = blocking

        if blocking is not None:
            log.msg("%s: BLOCKING DETECTED due to %s" % (self.input, blocking))
        else:
            log.msg("%s: No blocking detected" % self.input)

        if all(map(lambda x: x == None, [self.report['http_experiment_failure'],
                                         self.report['dns_experiment_failure'],
                                         blocking])):
            log.msg("")
            self.report['accessible'] = True
            log.msg("%s: is accessible" % self.input)
        else:
            log.msg("%s: is NOT accessible" % self.input)
            self.report['accessible'] = False

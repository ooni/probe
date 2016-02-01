# -*- encoding: utf-8 -*-

import json
from urlparse import urlparse

from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.endpoints import TCP4ClientEndpoint

from twisted.internet import defer
from twisted.python import usage

from ooni.utils import log

from ooni.utils.net import StringProducer, BodyReceiver
from ooni.templates import httpt, dnst, tcpt
from ooni.errors import failureToString

class TCPConnectProtocol(Protocol):
    def connectionMade(self):
        self.transport.loseConnection()

class TCPConnectFactory(Factory):
    def buildProtocol(self, addr):
        return TCPConnectProtocol()


class UsageOptions(usage.Options):
    optParameters = [
        ['url', 'u', None, 'Specify a single URL to test'],
        ['dns-discovery', 'd', None, 'Specify the dns discovery test helper'],
        ['backend', 'b', None, 'The web_consistency backend test helper'],
    ]


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
        'backend': 'web_connectivity',
        'dns-discovery': 'dns_discovery'
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

        self.report['tcp_connect'] = [
        ]

        self.hostname = urlparse(self.input).netloc
        if not self.hostname:
            raise Exception("Invalid input")

        self.control = {
            'tcp_connect': {},
            'dns_consistency': [],
            'http_requests': {
                'body_length': None,
                'headers': {}
            }
        }

    def dns_discovery(self):
        return self.performALookup(self.localOptions['dns-discovery'])

    def dns_consistency(self):
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

    def experiment_http_get_request(self):
        return self.doRequest(self.input)

    def compare_control_experiment(self, experiment_http_response,
                                   experiment_dns_answers):

        blocking = None

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
        else:
            blocking = 'http'
            self.report['body_length_match'] = False

        control_ips = set(self.control['dns']['ips'])
        experiment_ips = set(experiment_dns_answers)

        if len(control_ips.intersection(experiment_ips)) > 0:
            self.report['dns_consistency'] = 'consistent'
        else:
            if blocking is not None:
                blocking = 'dns'
            self.report['dns_consistency'] = 'inconsistent'

        for idx, result in enumerate(self.report['tcp_connect']):
            socket = "%s:%s" % (result['ip'], result['port'])
            control_status = self.control['tcp_connect'][socket]
            log.debug(str(result))
            if result['status']['success'] == False and \
                    control_status['status'] == True:
                self.report['tcp_connect'][idx]['status']['blocked'] = True
                blocking = 'tcp_ip'
            else:
                self.report['tcp_connect'][idx]['status']['blocked'] = False

        self.report['blocking'] = blocking

    @defer.inlineCallbacks
    def test_web_connectivity(self):
        results = yield defer.DeferredList([
            self.dns_discovery(),
            self.dns_consistency()
        ])

        self.report['client_resolver'] = None
        if results[0][0] == True:
            self.report['client_resolver']  = results[0][1][1]

        experiment_dns_answers = results[1][1]

        sockets = map(lambda x: "%s:80" % x, results[1][1])

        dl = [self.control_request(sockets)]
        for socket in sockets:
            dl.append(self.tcp_connect(socket))
        yield defer.DeferredList(dl)

        experiment_http_response = yield self.experiment_http_get_request()
        self.compare_control_experiment(experiment_http_response,
                                        experiment_dns_answers)

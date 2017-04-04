# -*- encoding: utf-8 -*-

import random

import ipaddr

from twisted.internet import defer, reactor
from twisted.python import usage
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.utils import log
from ooni.common.http_utils import extractTitle
from ooni.common.tcp_utils import TCPConnectFactory
from ooni.errors import failureToString

from ooni.templates import httpt, dnst

# These were retrieved from https://www.whatsapp.com/cidr.txt on 2016-10-12
WHATSAPP_IPV4 = """\
31.13.64.51/32
31.13.65.49/32
31.13.66.49/32
31.13.67.51/32
31.13.68.52/32
31.13.69.240/32
31.13.70.49/32
31.13.71.49/32
31.13.72.52/32
31.13.73.49/32
31.13.74.49/32
31.13.75.52/32
31.13.76.81/32
31.13.77.49/32
31.13.78.53/32
31.13.80.53/32
31.13.81.53/32
31.13.82.51/32
31.13.83.51/32
31.13.84.51/32
31.13.85.51/32
31.13.86.51/32
31.13.87.51/32
31.13.88.49/32
31.13.90.51/32
31.13.91.51/32
31.13.92.52/32
31.13.93.51/32
31.13.94.52/32
31.13.95.63/32
50.22.198.204/30
50.22.210.32/30
50.22.210.128/27
50.22.225.64/27
50.22.235.248/30
50.22.240.160/27
50.23.90.128/27
50.97.57.128/27
75.126.39.32/27
108.168.171.224/27
108.168.174.0/27
108.168.176.192/26
108.168.177.0/27
108.168.180.96/27
108.168.254.65/32
108.168.255.224/32
108.168.255.227/32
157.240.0.53/32
157.240.2.53/32
157.240.3.53/32
157.240.7.54/32
158.85.0.96/27
158.85.5.192/27
158.85.46.128/27
158.85.48.224/27
158.85.58.0/25
158.85.61.192/27
158.85.224.160/27
158.85.233.32/27
158.85.249.128/27
158.85.254.64/27
169.44.36.0/25
169.44.57.64/27
169.44.58.64/27
169.44.80.0/26
169.44.82.96/27
169.44.82.128/27
169.44.82.192/26
169.44.83.0/26
169.44.83.96/27
169.44.83.128/27
169.44.83.192/26
169.44.84.0/24
169.44.85.64/27
169.45.71.32/27
169.45.71.96/27
169.45.87.128/26
169.45.169.192/27
169.45.182.96/27
169.45.210.64/27
169.45.214.224/27
169.45.219.224/27
169.45.237.192/27
169.45.238.32/27
169.45.248.96/27
169.45.248.160/27
169.46.52.224/27
169.47.5.192/26
169.53.29.128/27
169.53.48.32/27
169.53.71.224/27
169.53.81.64/27
169.53.250.128/26
169.53.252.64/27
169.53.255.64/27
169.54.2.160/27
169.54.44.224/27
169.54.51.32/27
169.54.55.192/27
169.54.193.160/27
169.54.210.0/27
169.54.222.128/27
169.55.67.224/27
169.55.69.128/26
169.55.74.32/27
169.55.75.96/27
169.55.126.64/26
169.55.210.96/27
169.55.235.160/27
173.192.162.32/27
173.192.219.128/27
173.192.222.160/27
173.192.231.32/27
173.192.234.96/27
173.193.198.96/27
173.193.205.0/27
173.193.230.96/27
173.193.230.128/27
173.193.230.192/27
173.193.239.0/27
174.36.208.128/27
174.36.210.32/27
174.36.251.192/27
174.37.199.192/27
174.37.217.64/27
174.37.243.64/27
174.37.251.0/27
179.60.192.51/32
179.60.193.51/32
179.60.195.51/32
184.173.136.64/27
184.173.147.32/27
184.173.161.64/32
184.173.161.160/27
184.173.173.116/32
184.173.179.32/27
185.60.216.53/32
185.60.218.53/32
192.155.212.192/27
198.11.193.182/31
198.11.251.32/27
198.23.80.0/27
208.43.115.192/27
208.43.117.79/32
208.43.122.128/27"""

WHATSAPP_IPV6 = """\
2607:f0d0:1b01:d4::/64
2607:f0d0:1b02:14d::/64
2607:f0d0:1b04:32::/64
2607:f0d0:1b04:bb::/64
2607:f0d0:1b04:bc::/64
2607:f0d0:1b06::/64
2607:f0d0:1b06:4::/64
2607:f0d0:1e01:b1::/64
2607:f0d0:2102:229::/64
2607:f0d0:2601:37::/64
2607:f0d0:3003:1bc::/64
2607:f0d0:3003:1cd::/64
2607:f0d0:3004:136::/64
2607:f0d0:3004:174::/64
2607:f0d0:3005:183::/64
2607:f0d0:3005:1a3::/64
2607:f0d0:3006:84::/64
2607:f0d0:3006:af::/64
2607:f0d0:3801:38::/64
2607:f0d0:3801:14b::/64
2607:f0d0:3802:48::/64
2a03:2880:f200:c5:face:b00c::167/128
2a03:2880:f200:1c5:face:b00c::167/128
2a03:2880:f201:c5:face:b00c::167/128
2a03:2880:f202:c4:face:b00c::167/128
2a03:2880:f203:c5:face:b00c::167/128
2a03:2880:f204:c5:face:b00c::167/128
2a03:2880:f205:c5:face:b00c::167/128
2a03:2880:f206:c5:face:b00c::167/128
2a03:2880:f207:c5:face:b00c::167/128
2a03:2880:f208:c5:face:b00c::167/128
2a03:2880:f209:c5:face:b00c::167/128
2a03:2880:f20a:c5:face:b00c::167/128
2a03:2880:f20b:c5:face:b00c::167/128
2a03:2880:f20c:c6:face:b00c::167/128
2a03:2880:f20d:c5:face:b00c::167/128
2a03:2880:f20e:c5:face:b00c::167/128
2a03:2880:f20f:c6:face:b00c::167/128
2a03:2880:f210:c5:face:b00c::167/128
2a03:2880:f211:c5:face:b00c::167/128
2a03:2880:f212:c5:face:b00c::167/128
2a03:2880:f213:c5:face:b00c::167/128
2a03:2880:f213:80c5:face:b00c::167/128
2a03:2880:f214:c5:face:b00c::167/128
2a03:2880:f215:c5:face:b00c::167/128
2a03:2880:f216:c5:face:b00c::167/128
2a03:2880:f217:c5:face:b00c::167/128
2a03:2880:f218:c3:face:b00c::167/128
2a03:2880:f219:c5:face:b00c::167/128
2a03:2880:f21a:c5:face:b00c::167/128
2a03:2880:f21b:c5:face:b00c::167/128
2a03:2880:f21c:c5:face:b00c::167/128
2a03:2880:f21c:80c5:face:b00c::167/128
2a03:2880:f21f:c5:face:b00c::167/128
2a03:2880:f221:c5:face:b00c::167/128
2a03:2880:f222:c5:face:b00c::167/128
2a03:2880:f223:c5:face:b00c::167/128
2a03:2880:f225:c4:face:b00c::167/128
2a03:2880:f226:c6:face:b00c::167/128
2a03:2880:f227:c5:face:b00c::167/128"""

class DidNotConnect(Exception):
    pass

class WhatsAppNetwork(object):
    def __init__(self):
        self.ipv4_networks = []
        for ip in WHATSAPP_IPV4.split("\n"):
            try:
                self.ipv4_networks.append(ipaddr.IPv4Network(ip))
            except Exception:
                log.err("IP is wrong")
                log.msg(ip)
        self.ipv6_networks = map(ipaddr.IPv6Network,
                                 WHATSAPP_IPV6.split("\n"))

    def contains(self, ip_address):
        ip = ipaddr.IPAddress(ip_address)
        if isinstance(ip, ipaddr.IPv4Address):
            networks = self.ipv4_networks
        elif isinstance(ip, ipaddr.IPv6Address):
            networks = self.ipv6_networks
        else:
            raise RuntimeError("Should never happen")
        for network in networks:
            if network.Contains(ip):
                return True
        return False

class UsageOptions(usage.Options):
    optFlags = [
        ['all-endpoints', 'e', 'Should we attempt to connect to all whatsapp'
                               ' endpoints?'],
    ]

class WhatsappTest(httpt.HTTPTest, dnst.DNSTest):
    name = "Whatsapp"
    description = ("This test examines the reachability of WhatsApp "
                   " and WhatsApp's web interface (web.whatsapp.com) in your network.")
    author = "Arturo Filastò"
    version = "0.6.0"

    requiresRoot = False
    requiresTor = False
    followRedirects = True
    usageOptions = UsageOptions

    def setUp(self):
        # We need more time to ensure all the endpoints can timeout
        self.timeout = 16 * 20

    @defer.inlineCallbacks
    def test_registration_server(self):
        self.report['registration_server_failure'] = None
        self.report['registration_server_status'] = None

        url = 'https://v.whatsapp.net/v2/register'
        # Ensure I get back:
        # {"status": "fail", "reason": "missing_param", "param": "code"}

        try:
            yield self.doRequest(url, 'GET')
        except Exception as exc:
            failure_string = failureToString(defer.failure.Failure(exc))
            log.err("Failed to contact the registration server %s" % failure_string)
            self.report['registration_server_failure'] = failure_string
            self.report['registration_server_status'] = 'blocked'
            defer.returnValue(None)

        log.msg("Successfully connected to registration server!")
        self.report['registration_server_status'] = 'ok'

    @defer.inlineCallbacks
    def _test_whatsapp_web(self, url):
        try:
            response = yield self.doRequest(url, 'GET')
        except Exception as exc:
            failure_string = failureToString(defer.failure.Failure(exc))
            log.err("Failed to connect to whatsapp web %s" % failure_string)
            self.report['whatsapp_web_failure'] = failure_string
            self.report['whatsapp_web_status'] = 'blocked'
            defer.returnValue(None)

        title = extractTitle(response.body).strip()
        if title != "WhatsApp Web":
            self.report['whatsapp_web_status'] = 'blocked'

    @defer.inlineCallbacks
    def test_whatsapp_web(self):
        self.report['whatsapp_web_failure'] = None
        self.report['whatsapp_web_status'] = None

        yield self._test_whatsapp_web('https://web.whatsapp.com/')
        yield self._test_whatsapp_web('http://web.whatsapp.com/')
        if self.report['whatsapp_web_status'] != 'blocked':
            self.report['whatsapp_web_status'] = 'ok'

    def _test_connect_to_port(self, address, port):
        result = {
            'ip': address,
            'port': port,
            'status': {
                'success': None,
                'failure': None
            }
        }
        point = TCP4ClientEndpoint(reactor, address, port, timeout=10)
        d = point.connect(TCPConnectFactory())
        @d.addCallback
        def cb(p):
            result['status']['success'] = True
            result['status']['failure'] = False
            self.report['tcp_connect'].append(result)

        @d.addErrback
        def eb(failure):
            result['status']['success'] = False
            result['status']['failure'] = failureToString(failure)
            self.report['tcp_connect'].append(result)
            return failure

        return d

    @defer.inlineCallbacks
    def _test_connect(self, address):
        possible_ports = [443, 5222]

        connected = False
        for port in possible_ports:
            try:
                yield self._test_connect_to_port(address, port)
                connected = True
            except Exception:
                pass

        if connected == False:
            raise DidNotConnect

    @defer.inlineCallbacks
    def _test_endpoint(self, hostname, whatsapp_network):
        log.msg("Testing %s" % hostname)
        addresses = yield self.performALookup(hostname)
        ip_in_whats_app_network = False

        for address in addresses[:]:
            try:
                ip_in_whats_app_network |= whatsapp_network.contains(address)
            except ValueError:
                # This happens when it's not an IP
                addresses.remove(address)
                continue

        if ip_in_whats_app_network == False:
            log.msg("%s presents an INCONSISTENT DNS response" % hostname)
            self.report['whatsapp_endpoints_status'] = 'blocked'
            self.report['whatsapp_endpoints_dns_inconsistent'].append(hostname)

        dl = []
        for address in addresses:
            dl.append(self._test_connect(address))
        results = yield defer.DeferredList(dl, consumeErrors=True)

        tcp_blocked = False
        for success, result in results:
            if success == False:
                tcp_blocked = True

        if tcp_blocked == True:
            log.msg("%s is BLOCKED based on TCP" % hostname)
            self.report['whatsapp_endpoints_blocked'].append(hostname)
            self.report['whatsapp_endpoints_status'] = 'blocked'
        else:
            log.msg("No blocking detected via TCP on %s" % hostname)
            self.report['whatsapp_endpoints_status'] = 'ok'

    @defer.inlineCallbacks
    def test_endpoints(self):
        self.report['whatsapp_endpoints_status'] = None
        self.report['whatsapp_endpoints_dns_inconsistent'] = []
        self.report['whatsapp_endpoints_blocked'] = []

        self.report['tcp_connect'] = []

        possible_endpoints = map(lambda x: "e%s.whatsapp.net" % x, range(1, 17))
        whatsapp_network = WhatsAppNetwork()
        to_test_endpoints = []
        if self.localOptions.get('all-endpoints', False):
            to_test_endpoints += possible_endpoints
        else:
            to_test_endpoints += [random.choice(possible_endpoints)]
        for endpoint in to_test_endpoints:
            yield self._test_endpoint(endpoint, whatsapp_network)

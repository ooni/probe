# -*- encoding: utf-8 -*-

from twisted.internet import defer, reactor
from twisted.python import usage
from twisted.internet.endpoints import TCP4ClientEndpoint

try:
    from ooni.geoip import ip_to_location
except ImportError:
    # Backward compatibility with 1.6.0
    from ooni.geoip import IPToLocation as ip_to_location

from ooni.utils import log
from ooni.common.tcp_utils import TCPConnectFactory
from ooni.errors import failureToString

from ooni.templates import httpt, dnst


class UsageOptions(usage.Options):
    pass


FB_HOSTNAMES = {
    'stun': "stun.fbsbx.com",
    'b_api': "b-api.facebook.com",
    'b_graph': "b-graph.facebook.com",
    'edge': "edge-mqtt.facebook.com",
    'external_cdn': "external.xx.fbcdn.net",
    'scontent_cdn': "scontent.xx.fbcdn.net",
    'star': "star.c10r.facebook.com"
}

def is_facebook_ip(ip_address):
    """
    :return: True when the IP in questions belongs to the facebook ASN
    """
    try:
        location = ip_to_location(ip_address)
        return location['asn'] == 'AS32934'
    except:
        return False

class FacebookMessengerTest(httpt.HTTPTest, dnst.DNSTest):
    name = "Facebook Messenger"
    description = ("This test examines the reachability of Facebook "
                   "Messenger in your network.")
    author = "Arturo Filastò"
    version = "0.5.0"

    requiresRoot = False
    requiresTor = False
    followRedirects = True
    usageOptions = UsageOptions

    def setUp(self):
        for key in FB_HOSTNAMES.keys():
            self.report['facebook_{0}_dns_consistent'.format(key)] = None
            self.report['facebook_{0}_reachable'.format(key)] = None

        self.report['facebook_tcp_blocking'] = None
        self.report['facebook_dns_blocking'] = None
        self.report['tcp_connect'] = []

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
    def _test_tcp_connect(self, consistent_addresses):
        for key, addresses in consistent_addresses.items():
            if key == 'stun':
                # XXX we currently don't test stun
                continue

            dl = []
            for address in addresses:
                dl.append(self._test_connect_to_port(address, 443))
            results = yield defer.DeferredList(dl, consumeErrors=True)
            tcp_blocked = False
            for success, result in results:
                if success == False:
                    tcp_blocked = True

            if tcp_blocked == True:
                log.msg("{0} server is BLOCKED based on TCP".format(key))
            if len(addresses) > 0:
                self.report['facebook_{0}_reachable'.format(key)] = not tcp_blocked

    @defer.inlineCallbacks
    def _test_dns_resolution(self):
        consistent_addresses = {}
        for key, hostname in FB_HOSTNAMES.items():
            consistent_addresses[key] = []
            consistent = False
            try:
                addresses = yield self.performALookup(hostname)
                for address in addresses:
                    if is_facebook_ip(address):
                        consistent = True
                        consistent_addresses[key].append(address)
            except Exception:
                log.err("Failed to lookup {0}: {1}".format(key, hostname))
            finally:
                msg = "{0}: {1} appears to present ".format(key, hostname)
                if consistent == True:
                    msg += "consistent DNS"
                else:
                    msg += "INCONSISTENT DNS"
                log.msg(msg)
                self.report['facebook_{0}_dns_consistent'.format(key)] = consistent

        defer.returnValue(consistent_addresses)

    @defer.inlineCallbacks
    def test_endpoints(self):
        consistent_addresses = yield self._test_dns_resolution()
        yield self._test_tcp_connect(consistent_addresses)
        dns_blocking = False
        tcp_blocking = False
        for key in FB_HOSTNAMES.keys():
            if self.report['facebook_{0}_dns_consistent'.format(key)] == False:
                dns_blocking = True
                log.msg("{0} is BLOCKED due to DNS blocking".format(key))
                continue

            # XXX We ignore stun reachability as it requires UDP
            if key == 'stun':
                continue
            if self.report['facebook_{0}_reachable'.format(key)] == False:
                tcp_blocking = True
                log.msg("{0} is BLOCKED due to TCP/IP blocking".format(key))
                continue
            log.msg("{0} no blocking detected".format(key))

        self.report['facebook_tcp_blocking'] = tcp_blocking
        self.report['facebook_dns_blocking'] = dns_blocking

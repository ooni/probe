# -*- encoding: utf-8 -*-

from twisted.internet import defer, reactor
from twisted.python import usage
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.utils import log
from ooni.common.tcp_utils import TCPConnectFactory
from ooni.errors import failureToString

from ooni.templates import httpt

# These are taken from:
# https://github.com/telegramdesktop/tdesktop/blob/e6d94b5ee7d96a97ee5976dacb87bafd00beac1d/Telegram/SourceFiles/config.h#L205

TELEGRAM_DCS = [
    (1, "149.154.175.50", 443),
    (2, "149.154.167.51", 443),
    (3, "149.154.175.100", 443),
    (4, "149.154.167.91", 443),
    (5, "149.154.171.5", 443)
]

class UsageOptions(usage.Options):
    pass

class TelegramTest(httpt.HTTPTest):
    name = "Telegram"
    description = ("This test examines the reachability of Telegram "
                   "in your network.")
    author = "Arturo Filastò"
    version = "0.1.0"

    requiresRoot = False
    requiresTor = False
    followRedirects = True
    usageOptions = UsageOptions

    def setUp(self):
        self.report['telegram_tcp_blocking'] = None
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
    def _test_tcp_connect(self):
        for dc_id, address, port in TELEGRAM_DCS:
            dl = []
            log.debug("Testing %s:%s" % (address, port))
            dl.append(self._test_connect_to_port(address, port))

        results = yield defer.DeferredList(dl, consumeErrors=True)
        tcp_blocked = False
        for success, result in results:
            if success == False:
                tcp_blocked = True

        if tcp_blocked == True:
            self.report['telegram_tcp_blocking'] = True
            log.msg("telegram servers are BLOCKED based on TCP")
        else:
            self.report['telegram_tcp_blocking'] = False
            log.msg("telegram servers are not blocked")

    @defer.inlineCallbacks
    def test_endpoints(self):
        yield self._test_tcp_connect()

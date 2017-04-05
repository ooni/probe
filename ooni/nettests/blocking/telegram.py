# -*- encoding: utf-8 -*-

from twisted.internet import defer, reactor
from twisted.python import usage
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.utils import log
from ooni.common.http_utils import extractTitle
from ooni.common.tcp_utils import TCPConnectFactory
from ooni.errors import failureToString

from ooni.templates import httpt

# These are taken from:
# https://github.com/telegramdesktop/tdesktop/blob/e6d94b5ee7d96a97ee5976dacb87bafd00beac1d/Telegram/SourceFiles/config.h#L205
TELEGRAM_DCS = [
    (1, "149.154.175.50"),
    (2, "149.154.167.51"),
    (3, "149.154.175.100"),
    (4, "149.154.167.91"),
    (5, "149.154.171.5")
]

class UsageOptions(usage.Options):
    pass

class TelegramTest(httpt.HTTPTest):
    name = "Telegram"
    description = ("This test examines the reachability of Telegram "
                   "in your network.")
    author = "Arturo Filastò"
    version = "0.3.0"

    requiresRoot = False
    requiresTor = False
    followRedirects = True
    usageOptions = UsageOptions

    def setUp(self):
        self.report['telegram_tcp_blocking'] = None
        self.report['telegram_http_blocking'] = None
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
        for dc_id, address in TELEGRAM_DCS:
            dl = []
            log.debug("Testing %s:443|80" % (address))
            dl.append(self._test_connect_to_port(address, 443))
            dl.append(self._test_connect_to_port(address, 80))

        results = yield defer.DeferredList(dl, consumeErrors=True)
        tcp_blocked = True
        for success, result in results:
            if success == True:
                tcp_blocked = False

        if tcp_blocked == True:
            self.report['telegram_tcp_blocking'] = True
            log.msg("Telegram servers are BLOCKED based on TCP")
        else:
            self.report['telegram_tcp_blocking'] = False
            log.msg("Telegram servers are not blocked based on TCP")

    @defer.inlineCallbacks
    def _test_http_request(self):
        http_blocked = True
        for dc_id, address in TELEGRAM_DCS:
            if http_blocked == False:
                break
            for port in [80, 443]:
                url = 'http://{}:{}'.format(address, port)
                try:
                    response = yield self.doRequest(url, 'POST')
                except Exception as exc:
                    failure_string = failureToString(defer.failure.Failure(exc))
                    log.err("Failed to connect to {}: {}".format(url, failure_string))
                    continue
                log.debug("Got back status code {}".format(response.code))
                log.debug("{}".format(response.body))
                if response.code == 501:
                    http_blocked = False
                    break

        if http_blocked == True:
            self.report['telegram_http_blocking'] = True
            log.msg("Telegram servers are BLOCKED based on HTTP")
        else:
            self.report['telegram_http_blocking'] = False
            log.msg("Telegram servers are not blocked based on HTTP")

    @defer.inlineCallbacks
    def _test_telegram_web(self, url):
        try:
            response = yield self.doRequest(url, 'GET')
        except Exception as exc:
            failure_string = failureToString(defer.failure.Failure(exc))
            log.err("Failed to connect to telegram web %s" % failure_string)
            self.report['telegram_web_failure'] = failure_string
            self.report['telegram_web_status'] = 'blocked'
            defer.returnValue(None)

        title = extractTitle(response.body).strip()
        if title != "Telegram Web":
            self.report['telegram_web_status'] = 'blocked'

    @defer.inlineCallbacks
    def test_telegram_web(self):
        self.report['telegram_web_failure'] = None
        self.report['telegram_web_status'] = None

        yield self._test_telegram_web('https://web.telegram.org/')
        yield self._test_telegram_web('http://web.telegram.org/')
        if self.report['telegram_web_status'] != 'blocked':
            self.report['telegram_web_status'] = 'ok'


    @defer.inlineCallbacks
    def test_endpoints(self):
        yield self._test_tcp_connect()
        yield self._test_http_request()

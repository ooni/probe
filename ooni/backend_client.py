import os
import json

from urlparse import urljoin, urlparse

from twisted.web.error import Error
from twisted.web.client import Agent, Headers
from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from twisted.python.versions import Version
from twisted import version as _twisted_version
_twisted_14_0_2_version = Version('twisted', 14, 0, 2)

from ooni import errors as e, constants
from ooni.settings import config
from ooni.utils import log, onion
from ooni.utils.net import BodyReceiver, StringProducer, Downloader
from ooni.utils.socks import TrueHeadersSOCKS5Agent


def guess_backend_type(address):
    if address is None:
        raise e.InvalidAddress
    if onion.is_onion_address(address):
        return 'onion'
    elif address.startswith('https://'):
        return 'https'
    elif address.startswith('http://'):
        return 'http'
    else:
        raise e.InvalidAddress

class OONIBClient(object):
    def __init__(self, address=None, settings={}):
        self.base_headers = {}
        self.backend_type = settings.get('type', None)
        self.base_address = settings.get('address', address)
        self.front = settings.get('front', '').encode('ascii')

        if self.backend_type is None:
            self.backend_type = guess_backend_type(self.base_address)
        self.backend_type = self.backend_type.encode('ascii')

        self.settings = {
            'type': self.backend_type,
            'address': self.base_address,
            'front': self.front
        }
        self._setupBaseAddress()

    def _setupBaseAddress(self):
        parsed_address = urlparse(self.base_address)
        if self.backend_type == 'onion':
            if not onion.is_onion_address(self.base_address):
                log.err("Invalid onion address.")
                raise e.InvalidAddress(self.base_address)
            if parsed_address.scheme in ('http', 'httpo'):
                self.base_address = ("http://%s" % parsed_address.netloc)
            else:
                self.base_address = ("%s://%s" % (parsed_address.scheme,
                                                  parsed_address.netloc))
        elif self.backend_type == 'http':
            self.base_address = ("http://%s" % parsed_address.netloc)
        elif self.backend_type == 'https':
            self.base_address = ("https://%s" % parsed_address.netloc)
        elif self.backend_type == 'cloudfront':
            self.base_headers['Host'] = [parsed_address.netloc]
            self.base_address = ("https://%s" % self.front)
        self.base_address = self.base_address.encode('ascii')

    def isSupported(self):
        if self.backend_type in ("https", "cloudfront"):
            if _twisted_version < _twisted_14_0_2_version:
                log.err("HTTPS and cloudfronted backends require "
                        "twisted > 14.0.2.")
                return False
        elif self.backend_type == "http":
            if config.advanced.insecure_backend is not True:
                log.err("Plaintext backends are not supported. To "
                        "enable at your own risk set "
                        "advanced->insecure_backend to true")
                return False
        elif self.backend_type == "onion":
            # XXX add an extra check to ensure tor is running
            if not config.tor_state and config.tor.socks_port is None:
                return False
        return True

    def isReachable(self):
        raise NotImplemented

    def _request(self, method, urn, genReceiver, bodyProducer=None, retries=3):
        if self.backend_type == 'onion':
            agent = TrueHeadersSOCKS5Agent(reactor,
                                           proxyEndpoint=TCP4ClientEndpoint(reactor,
                                                                            '127.0.0.1',
                                                                            config.tor.socks_port))
        else:
            agent = Agent(reactor)

        attempts = 0

        finished = defer.Deferred()

        def perform_request(attempts):
            uri = urljoin(self.base_address, urn)
            d = agent.request(method, uri, bodyProducer=bodyProducer,
                              headers=Headers(self.base_headers))

            @d.addCallback
            def callback(response):
                try:
                    content_length = int(response.headers.getRawHeaders('content-length')[0])
                except:
                    content_length = None
                response.deliverBody(genReceiver(finished, content_length))

            def errback(err, attempts):
                # We we will recursively keep trying to perform a request until
                # we have reached the retry count.
                if attempts < retries:
                    log.err("Lookup failed. Retrying.")
                    attempts += 1
                    perform_request(attempts)
                else:
                    log.err("Failed. Giving up.")
                    finished.errback(err)

            d.addErrback(errback, attempts)

        perform_request(attempts)

        return finished

    def queryBackend(self, method, urn, query=None, retries=3):
        log.debug("Querying backend {0}{1} with {2}".format(self.base_address,
                                                         urn, query))
        bodyProducer = None
        if query:
            bodyProducer = StringProducer(json.dumps(query))

        def genReceiver(finished, content_length):
            def process_response(s):
                # If empty string then don't parse it.
                if not s:
                    return
                try:
                    response = json.loads(s)
                except ValueError:
                    raise e.get_error(None)
                if 'error' in response:
                    log.debug("Got this backend error message %s" % response)
                    raise e.get_error(response['error'])
                return response

            return BodyReceiver(finished, content_length, process_response)

        return self._request(method, urn, genReceiver, bodyProducer, retries)

    def download(self, urn, download_path):

        def genReceiver(finished, content_length):
            return Downloader(download_path, finished, content_length)

        return self._request('GET', urn, genReceiver)

class BouncerClient(OONIBClient):
    def isReachable(self):
        return defer.succeed(True)

    @defer.inlineCallbacks
    def lookupTestCollector(self, net_tests):
        try:
            test_collector = yield self.queryBackend('POST', '/bouncer/net-tests',
                                                     query={'net-tests': net_tests})
        except Exception as exc:
            log.exception(exc)
            raise e.CouldNotFindTestCollector

        defer.returnValue(test_collector)

    @defer.inlineCallbacks
    def lookupTestHelpers(self, test_helper_names):
        try:
            test_helper = yield self.queryBackend('POST', '/bouncer/test-helpers',
                                                  query={'test-helpers': test_helper_names})
        except Exception as exc:
            log.exception(exc)
            raise e.CouldNotFindTestHelper

        if not test_helper:
            raise e.CouldNotFindTestHelper

        defer.returnValue(test_helper)


class CollectorClient(OONIBClient):
    def isReachable(self):
        # XXX maybe in the future we can have a dedicated API endpoint to
        # test the reachability of the collector.
        d = self.queryBackend('GET', '/invalidpath')

        @d.addCallback
        def cb(_):
            # We should never be getting an acceptable response for a
            # request to an invalid path.
            return False

        @d.addErrback
        def err(failure):
            failure.trap(Error)
            return failure.value.status == '404'

        return d

    def getInputPolicy(self):
        return self.queryBackend('GET', '/policy/input')

    def getNettestPolicy(self):
        return self.queryBackend('GET', '/policy/nettest')

    def createReport(self, test_details):
        request = {
            'software_name': test_details['software_name'],
            'software_version': test_details['software_version'],
            'probe_asn': test_details['probe_asn'],
            'probe_cc': test_details['probe_cc'],
            'test_name': test_details['test_name'],
            'test_version': test_details['test_version'],
            'test_start_time': test_details['test_start_time'],
            'input_hashes': test_details['input_hashes'],
            'data_format_version': test_details['data_format_version'],
            'format': 'json'
        }
        # import values from the environment
        request.update([(k.lower(),v) for (k,v) in os.environ.iteritems()
                        if k.startswith('PROBE_')])

        return self.queryBackend('POST', '/report', query=request)

    def updateReport(self, report_id, serialization_format, entry_content):
        request = {
            'format': serialization_format,
            'content': entry_content
        }
        return self.queryBackend('POST', '/report/%s' % report_id,
                                 query=request)


    def closeReport(self, report_id):
        return self.queryBackend('POST', '/report/' + report_id + '/close')

class WebConnectivityClient(OONIBClient):
    def isReachable(self):
        d = self.queryBackend('GET', '/status')

        @d.addCallback
        def cb(result):
            if result.get("status", None) != "ok":
                return False
            return True

        @d.addErrback
        def err(_):
            return False

        return d

    def control(self, http_request, tcp_connect):
        request = {
            'http_request': http_request,
            'tcp_connect': tcp_connect
        }
        return self.queryBackend('POST', '/', query=request)


def get_preferred_bouncer():
    preferred_backend = config.advanced.get(
        "preferred_backend", "onion"
    )
    bouncer_address = getattr(
        constants, "CANONICAL_BOUNCER_{0}".format(
            preferred_backend.upper()
        )
    )
    if preferred_backend == "cloudfront":
        return BouncerClient(
            settings={
                'address': bouncer_address[0],
                'front': bouncer_address[1],
                'type': 'cloudfront'
        })
    else:
        return BouncerClient(bouncer_address)

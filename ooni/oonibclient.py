import os
import json

from hashlib import sha256

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from ooni.deck import Deck, InputFile
from ooni import errors as e
from ooni.settings import config
from ooni.utils import log
from ooni.utils.net import BodyReceiver, StringProducer, Downloader
from ooni.utils.trueheaders import TrueHeadersSOCKS5Agent

class Collector(object):
    def __init__(self, address):
        self.address = address

        self.nettest_policy = None
        self.input_policy = None
    
    @defer.inlineCallbacks
    def loadPolicy(self):
        # XXX implement caching of policies
        oonibclient = OONIBClient(self.address)
        log.msg("Looking up nettest policy for %s" % self.address)
        self.nettest_policy = yield oonibclient.getNettestPolicy()
        log.msg("Looking up input policy for %s" % self.address)
        self.input_policy = yield oonibclient.getInputPolicy()

    def validateInput(self, input_hash):
        for i in self.input_policy:
            if i['id'] == input_hash:
                return True
        return False

    def validateNettest(self, nettest_name):
        for i in self.nettest_policy:
            if nettest_name == i['name']:
                return True
        return False

class OONIBClient(object):
    retries = 3

    def __init__(self, address):
        if address.startswith('httpo://'):
            self.address = address.replace('httpo://', 'http://')
            self.agent = TrueHeadersSOCKS5Agent(reactor,
                proxyEndpoint=TCP4ClientEndpoint(reactor, '127.0.0.1',
                    config.tor.socks_port))

        elif address.startswith('https://'):
            log.err("HTTPS based bouncers are currently not supported.")


    def _request(self, method, urn, genReceiver, bodyProducer=None):
        attempts = 0

        finished = defer.Deferred()

        def perform_request(attempts):
            uri = self.address + urn
            headers = {}
            d = self.agent.request(method, uri, bodyProducer=bodyProducer)

            @d.addCallback
            def callback(response):
                content_length = int(response.headers.getRawHeaders('content-length')[0])
                response.deliverBody(genReceiver(finished, content_length))

            def errback(err, attempts):
                # We we will recursively keep trying to perform a request until
                # we have reached the retry count.
                if attempts < self.retries:
                    log.err("Lookup failed. Retrying.")
                    log.exception(err)
                    attempts += 1
                    perform_request(attempts)
                else:
                    log.err("Failed. Giving up.")
                    finished.errback(err)
            d.addErrback(errback, attempts)

        perform_request(attempts)

        return finished

    def queryBackend(self, method, urn, query=None):
        bodyProducer = None
        if query:
            bodyProducer = StringProducer(json.dumps(query))
        
        def genReceiver(finished, content_length):
            def process_response(s):
                try:
                    response = json.loads(s)
                except ValueError:
                    raise e.get_error(None)
                if 'error' in response:
                    print "Got this backend error message %s" % response
                    log.err("Got this backend error message %s" % response)
                    raise e.get_error(response['error'])
                return response
            return BodyReceiver(finished, content_length, process_response)

        return self._request(method, urn, genReceiver, bodyProducer)

    def download(self, urn, download_path):

        def genReceiver(finished, content_length):
            return Downloader(download_path, finished, content_length)

        return self._request('GET', urn, genReceiver)
    
    def getNettestPolicy(self):
        pass

    def getInput(self, input_hash):
        input_file = InputFile(input_hash)
        if input_file.descriptorCached:
            return defer.succeed(input_file)
        else:
            d = self.queryBackend('GET', '/input/' + input_hash)

            @d.addCallback
            def cb(descriptor):
                input_file.load(descriptor)
                input_file.save()
                return input_file

            @d.addErrback
            def err(err):
                log.err("Failed to get descriptor for input %s" % input_hash)
                log.exception(err)

            return d

    def getInputList(self):
        return self.queryBackend('GET', '/input')

    def downloadInput(self, input_hash):
        input_file = InputFile(input_hash)

        if input_file.fileCached:
            return defer.succeed(input_file)
        else:
            d = self.download('/input/'+input_hash+'/file', input_file.cached_file)

            @d.addCallback
            def cb(res):
                input_file.verify()
                return input_file

            @d.addErrback
            def err(err):
                log.err("Failed to download the input file %s" % input_hash)
                log.exception(err)

            return d

    def getInputPolicy(self):
        return self.queryBackend('GET', '/policy/input')

    def getNettestPolicy(self):
        return self.queryBackend('GET', '/policy/nettest')

    def getDeckList(self):
        return self.queryBackend('GET', '/deck')

    def getDeck(self, deck_hash):
        deck = Deck(deck_hash)
        if deck.descriptorCached:
            return defer.succeed(deck)
        else:
            d = self.queryBackend('GET', '/deck/' + deck_hash)

            @d.addCallback
            def cb(descriptor):
                deck.load(descriptor)
                deck.save()
                return deck

            @d.addErrback
            def err(err):
                log.err("Failed to get descriptor for deck %s" % deck_hash)
                print err
                log.exception(err)

            return d

    def downloadDeck(self, deck_hash):
        deck = Deck(deck_hash)
        if deck.fileCached:
            return defer.succeed(deck)
        else:
            d = self.download('/deck/'+deck_hash+'/file', deck.cached_file)

            @d.addCallback
            def cb(res):
                deck.verify()
                return deck

            @d.addErrback
            def err(err):
                log.err("Failed to download the deck %s" % deck_hash)
                print err
                log.exception(err)

            return d

    @defer.inlineCallbacks
    def lookupTestCollector(self, test_name):
        try:
            test_collector = yield self.queryBackend('POST', '/bouncer',
                    query={'test-collector': test_name})
        except Exception:
            raise e.CouldNotFindTestCollector

        defer.returnValue(test_collector)

    @defer.inlineCallbacks
    def lookupTestHelpers(self, test_helper_names):
        try:

            test_helper = yield self.queryBackend('POST', '/bouncer', 
                            query={'test-helpers': test_helper_names})
        except Exception, exc:
            log.exception(exc)
            raise e.CouldNotFindTestHelper

        if not test_helper:
            raise e.CouldNotFindTestHelper

        defer.returnValue(test_helper)

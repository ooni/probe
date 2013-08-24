import os
import json

from hashlib import sha256

from twisted.internet import defer, reactor

from ooni.utils.txagentwithsocks import Agent

from ooni import errors as e
from ooni.settings import config
from ooni.utils import log
from ooni.utils.net import BodyReceiver, StringProducer, Downloader

class InputFile(object):
    def __init__(self, input_hash):
        self.id = input_hash
        cached_input_dir = os.path.join(config.advanced.data_dir,
                'inputs')
        cache_path = os.path.join(cached_input_dir, input_hash)
        self.cached_file = cache_path
        self.cached_descriptor = cache_path + '.desc'
    
    @property
    def descriptorCached(self):
        if os.path.exists(self.cached_descriptor):
            with open(self.cached_descriptor) as f:
                descriptor = json.load(f)
                self.load(descriptor)
            return True
        return False
    
    @property
    def fileCached(self):
        if os.path.exists(self.cached_file):
            try:
                self.verify()
            except AssertionError:
                log.err("The input %s failed validation. Going to consider it not cached." % self.id)
                return False
            return True
        return False

    def save(self):
        with open(self.cached_descriptor, 'w+') as f:
            json.dump({
                'name': self.name,
                'id': self.id,
                'version': self.version,
                'author': self.author,
                'date': self.date,
                'description': self.description
            }, f)
    
    def load(self, descriptor):
        self.name = descriptor['name']
        self.version = descriptor['version']
        self.author = descriptor['author']
        self.date = descriptor['date']
        self.description = descriptor['description']

    def verify(self):
        digest = os.path.basename(self.cached_file)
        with open(self.cached_file) as f:
            file_hash = sha256(f.read())
            assert file_hash.hexdigest() == digest

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
    def __init__(self, address):
        self.address = address
        self.agent = Agent(reactor, sockshost="127.0.0.1", 
                           socksport=config.tor.socks_port)

    def _request(self, method, urn, genReceiver, bodyProducer=None):
        finished = defer.Deferred()

        uri = self.address + urn
        headers = {}
        d = self.agent.request(method, uri, bodyProducer=bodyProducer)

        @d.addCallback
        def callback(response):
            content_length = int(response.headers.getRawHeaders('content-length')[0])
            response.deliverBody(genReceiver(finished, content_length))

        @d.addErrback
        def eb(err):
            finished.errback(err)

        return finished

    def queryBackend(self, method, urn, query=None):
        bodyProducer = None
        if query:
            bodyProducer = StringProducer(json.dumps(query))
    
        def genReceiver(finished, content_length):
            return BodyReceiver(finished, content_length, json.loads)

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

    @defer.inlineCallbacks
    def lookupTestHelpers(self, test_helper_names):
        try:
            test_helpers = yield self.queryBackend('POST', '/bouncer', 
                            query={'test-helpers': test_helper_names})
        except Exception:
            raise e.CouldNotFindTestHelper

        if not test_helpers:
            raise e.CouldNotFindTestHelper

        defer.returnValue(test_helpers)


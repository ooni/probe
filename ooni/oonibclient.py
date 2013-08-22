import os
import json

from hashlib import sha256

from twisted.internet import defer, reactor
from twisted.web.client import Agent

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

class OONIBClient(object):
    def __init__(self, address):
        self.address = address
        self.agent = Agent(reactor)
        self.input_files = {}

    def _request(self, method, urn, genReceiver, bodyProducer=None):
        finished = defer.Deferred()

        uri = self.address + urn
        d = self.agent.request(method, uri, bodyProducer)

        @d.addCallback
        def callback(response):
            content_length = response.headers.getRawHeaders('content-length')
            response.deliverBody(genReceiver(finished, content_length))

        @d.addErrback
        def eb(err):
            finished.errback(err)

        return finished

    def queryBackend(self, method, urn, query=None):
        bodyProducer = None
        if query:
            bodyProducer = StringProducer(json.dumps(query), bodyProducer)
    
        def genReceiver(finished, content_length):
            return BodyReceiver(finished, content_length, json.loads)

        return self._request(method, urn, genReceiver, bodyProducer)

    def download(self, urn, download_path):

        def genReceiver(finished, content_length):
            return Downloader(download_path, finished, content_length)

        return self._request('GET', urn, genReceiver)
    
    def getNettestPolicy(self):
        pass

    def queryBouncer(self, requested_helpers):
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
        pass

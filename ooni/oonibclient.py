from hashlib import sha256

import json

from twisted.internet import defer, reactor
from twisted.web.client import Agent

from ooni.utils.net import BodyReceiver, StringProducer, Downloader

class InputFile(object):
    def __init__(self, descriptor):
        self.id = descriptor['id']
        self.name = descriptor['name']
        self.version = descriptor['version']
        self.author = descriptor['author']
        self.date = descriptor['date']

        self.file_path = None

    def verify(self):
        digest = os.path.basename(self.file_path)
        with open(self.file_path) as f:
            file_hash = sha256(f.read())
            return file_hash.hexdigest() == digest
        return False

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
        try:
            return defer.succeed(self.input_files[input_hash])
        except KeyError:
            d = self.queryBackend('GET', '/input/' + input_hash)
            @d.addCallback
            def cb(descriptor):
                self.input_files[input_hash] = InputFile(descriptor)
                return self.input_files[input_hash]
            @d.addErrback
            def err(err):
                log.err("Failed to get descriptor for input %s" % input_hash)
                log.exception(err)
            return d

    def getInputList(self):
        return self.queryBackend('GET', '/input')

    def downloadInput(self, input_hash, download_path):
        return self.download('/input/'+input_hash+'/file', download_path)

    def getInputPolicy(self):
        pass

import json

from twisted.internet import defer, reactor
from twisted.web.client import Agent

from ooni.utils.net import BodyReceiver, StringProducer

class InputFile(object):
    def __init__(self, id, name=None, description=None, 
                 version=None, author=None, date=None):
        self.id = id
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.date = date

        self._file = None

class Deck(object):
    pass

class OONIBClient(object):
    def __init__(self, address):
        self.address = address
        self.agent = Agent(reactor)

    def queryBackend(self, method, urn, query=None):
        finished = defer.Deferred()

        bodyProducer = None
        if query:
            bodyProducer = StringProducer(json.dumps(query))

        uri = self.address + urn
        d = self.agent.request(method, uri, bodyProducer)
        @d.addCallback
        def cb(response):
            content_length = response.headers.getRawHeaders('content-length')
            response.deliverBody(BodyReceiver(finished, content_length, json.loads))

        @d.addErrback
        def eb(err):
            finished.errback(err)

        return finished

    def getNettestPolicy(self):
        pass

    def queryBouncer(self, requested_helpers):
        pass

    def getInputPolicy(self):
        pass



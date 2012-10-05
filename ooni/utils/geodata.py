import re
from twisted.web.client import Agent
from twisted.internet import reactor, defer, protocol

class BodyReceiver(protocol.Protocol):
    def __init__(self, finished):
        self.finished = finished
        self.data = ""

    def dataReceived(self, bytes):
        self.data += bytes

    def connectionLost(self, reason):
        self.finished.callback(self.data)

@defer.inlineCallbacks
def myIP():
    target_site = 'https://check.torproject.org/'
    regexp = "Your IP address appears to be: <b>(.+?)<\/b>"

    myAgent = Agent(reactor)
    result = yield myAgent.request('GET', target_site)
    finished = defer.Deferred()
    result.deliverBody(BodyReceiver(finished))
    body = yield finished

    match = re.search(regexp, body)
    try:
        myip = match.group(1)
    except:
        myip = "unknown"

    return myip



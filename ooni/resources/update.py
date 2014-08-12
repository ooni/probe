import os

from twisted.internet import reactor, defer, protocol
from twisted.web.client import RedirectAgent, Agent

from ooni.settings import config
from ooni.resources import inputs, geoip

agent = RedirectAgent(Agent(reactor))


class SaveToFile(protocol.Protocol):
    def __init__(self, finished, filesize, filename):
        self.finished = finished
        self.remaining = filesize
        self.outfile = open(filename, 'wb')

    def dataReceived(self, bytes):
        if self.remaining:
            display = bytes[:self.remaining]
            self.outfile.write(display)
            self.remaining -= len(display)
        else:
            self.outfile.close()

    def connectionLost(self, reason):
        self.outfile.close()
        self.finished.callback(None)


@defer.inlineCallbacks
def download_resource(resources):
    for filename, resource in resources.items():
        print "Downloading %s" % filename

        filename = os.path.join(config.resources_directory, filename)
        response = yield agent.request("GET", resource['url'])
        finished = defer.Deferred()
        response.deliverBody(SaveToFile(finished, response.length, filename))
        yield finished

        if resource['action'] is not None:
            yield defer.maybeDeferred(resource['action'],
                                      filename,
                                      *resource['action_args'])
        print "%s written." % filename


def download_inputs():
    return download_resource(inputs)


def download_geoip():
    return download_resource(geoip)

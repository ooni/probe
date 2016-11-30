"""
    This file contains function proxies that request to MeasurementKit to
    run a specific test and pass the response back using a deferred.

    It's not the job of this module to start MeasurementKit. Throughout
    this module we will assume that MeasurementKit is already running.

    Example usage:

        port = 9876
        password = "antani"
        url = "http://www.google.com/"
        settings = {
            "nameserver": "8.8.8.8:53",
            "dns/resolver": "system",
            "backend": "https://a.collector.test.ooni.io:4444"
        }

        d = proxy.web_connectivity(port, password, url, settings)
        @d.addCallback
        def cb(test_keys):
            print(test_keys)
"""

from __future__ import print_function

import collections
import json

from twisted.internet import defer
from twisted.internet import protocol
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint
from twisted.protocols.basic import LineReceiver

from ooni.utils import log

class MkControlRecord(object):
    """
        Response returned by MK. Status is either "OK" or "ERR error" and
        message is a Python dictionary containing the test keys.
    """

    def __init__(self):
        self.done = None
        self.input = None
        self.message = None
        self.status = None

class MkControlProtocol(LineReceiver):
    """
        Basic control protocol with which you can send requests and get the
        corresponding responses using deferreds.

        See https://github.com/measurement-kit/measurement-kit/blob/master/doc/mk-ctrl.md
    """

    MAX_LENGTH = 10 * 1024 * 1024

    def __init__(self):
        self.linesReceived = []
        self.pending = collections.deque()

    def connectionLost(self, reason=protocol.connectionDone):
        #log.msg("Connection closed: %s" % str(reason))
        for record in self.pending:
            if record.done is not None:
                record.done.errback(reason)
        self.pending.clear()

    def sendCommand(self, line):
        #log.msg("Sending command: %s" % str(line))
        self.sendLine(line)
        record = MkControlRecord()
        record.done = defer.Deferred()
        record.input = line
        self.pending.append(record)
        return record.done

    def lineReceived(self, line):
        #log.msg("Received line: %s" % str(line)[:128])
        if not self.pending:
            log.warn("Protocol violation: response to no pending request")
            self.transport.loseConnection()
            return
        self.linesReceived.append(line)
        if len(self.linesReceived) < 2:
            return
        record = self.pending.popleft()
        record.status = self.linesReceived[0]
        record.message = self.linesReceived[1]
        record.done, done = None, record.done
        del self.linesReceived[:]
        #raise Exception(str(type(reply.message)))
        try:
            record.message = json.loads(record.message.decode("utf-8"))
        except ValueError as exc:
            log.msg("Cannot decode object for '%s': %s" % (
                    record.input, str(exc)))
            done.errback(exc)
            return
        #log.msg("Callbacking")
        done.callback(record)

class MkControlProtocolFactory(protocol.Factory):
    def buildProtocol(self, _):
        return MkControlProtocol()

def connect(port):
    endpoint = TCP4ClientEndpoint(reactor, "127.0.0.1", port)
    return endpoint.connect(MkControlProtocolFactory())

def authenticate(protocol, password):
    return protocol.sendCommand("AUTH " + password)

class MkAuthenticationError(Exception):
    pass

class MkWebConnectivityError(Exception):
    pass

@defer.inlineCallbacks
def web_connectivity(port, password, url, settings):

    protocol = yield connect(port)
    reply = yield authenticate(protocol, password)

    if reply.status != "OK":
        raise MkAuthenticationError

    reply = yield protocol.sendCommand(
        "RUN web_connectivity " + json.dumps({
            "input": url,
            "settings": settings
        }))

    if reply.status != "OK":
        raise MkWebConnectivityError

    protocol.transport.loseConnection()

    defer.returnValue(reply.message)

import json
import random
import string

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.protocols import basic
from twisted.web import resource, server, static, http
from twisted.web.microdom import escape

server.version = "Apache"

class HTTPRandomPage(resource.Resource):
    """
    This generates a random page of arbitrary length and containing the string
    selected by the user.
    The format is the following:
    /random/<length>/<keyword>
    """
    isLeaf = True
    def _gen_random_string(self, length):
        return ''.join(random.choice(string.letters) for x in range(length))

    def genRandomPage(self, length=100, keyword=None):
        data = self._gen_random_string(length/2)
        if keyword:
            data += keyword
        data += self._gen_random_string(length - length/2)
        data += '\n'
        return data

    def render(self, request):
        length = 100
        keyword = None
        path_parts = request.path.split('/')
        if len(path_parts) > 2:
            length = int(path_parts[2])
            if length > 100000:
                length = 100000

        if len(path_parts) > 3:
            keyword = escape(path_parts[3])

        return self.genRandomPage(length, keyword)

class HTTPReturnHeaders(resource.Resource):
    """
    This returns the headers being sent by the client in JSON format.
    """
    isLeaf = True
    def render(self, request):
        req_headers = request.getAllHeaders()
        return json.dumps(req_headers)

class HTTPSendHeaders(resource.Resource):
    """
    This sends to the client the headers that they send inside of the POST
    request encoded in json.
    """
    isLeaf = True
    def render_POST(self, request):
        headers = json.loads(request.content.read())
        for header, value in headers.items():
            request.setHeader(str(header), str(value))
        return ''

class HTTPBackend(resource.Resource):
    def __init__(self):
        resource.Resource.__init__(self)
        self.putChild('random', HTTPRandomPage())
        self.putChild('returnheaders', HTTPReturnHeaders())
        self.putChild('sendheaders', HTTPSendHeaders())

class DebugProtocol(http.HTTPChannel):
    def headerReceived(self, line):
        print "[HEADER] %s" % line
        http.HTTPChannel.headerReceived(self, line)

    def allContentReceived(self):
        print self.requests[-1].getAllHeaders()
        self.transport.loseConnection()
        self.connectionLost("Normal closure")

class DebugHTTPServer(http.HTTPFactory):
    protocol = DebugProtocol

    def buildProtocol(self, addr):
        print "Got connection from %s" % addr
        p = protocol.ServerFactory.buildProtocol(self, addr)
        p.timeOut = self.timeOut
        return p


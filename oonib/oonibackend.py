"""
    ooni backend
    ************

    This is the backend system responsible for running certain services that
    are useful for censorship detection.
"""
import json
import random
import string

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.protocols import basic
from twisted.web import resource, server, static
from twisted.web.microdom import escape
from twisted.names import dns

from oonib.httpbackend import HTTPBackend
from oonib.dnsbackend import ProxyDNSServer
from oonib.b0wser import B0wserServer

# This tells twisted to set the
server.version = "Apache"

application = service.Application('oonibackend')
serviceCollection = service.IServiceCollection(application)
internet.TCPServer(2000, server.Site(HTTPBackend())).setServiceParent(serviceCollection)

# Start the DNS Server related services
TCPDNSServer = ProxyDNSServer()
internet.TCPServer(8002, TCPDNSServer).setServiceParent(serviceCollection)
UDPFactory = dns.DNSDatagramProtocol(TCPDNSServer)
internet.UDPServer(5354, UDPFactory).setServiceParent(serviceCollection)

# Start the ooni backend thing
b0wser = B0wserServer()
internet.TCPServer(9666, b0wser).setServiceParent(serviceCollection)

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

from backend.httpbackend import HTTPBackend
from backend.dnsbackend import ProxyDNSServer

# This tells twisted to set the
server.version = "Apache"

application = service.Application('oonibackend')
serviceCollection = service.IServiceCollection(application)
internet.TCPServer(8000, server.Site(HTTPBackend())).setServiceParent(serviceCollection)

# Start the DNS Server related services
TCPDNSServer = ProxyDNSServer()
internet.TCPServer(8002, TCPDNSServer).setServiceParent(serviceCollection)
UDPFactory = dns.DNSDatagramProtocol(TCPDNSServer)
internet.UDPServer(5353, UDPFactory).setServiceParent(serviceCollection)


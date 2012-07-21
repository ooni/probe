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

from ooni.utils import Storage
from ooni.utils.config import Config

from oonib.backends.http import HTTPBackend
from oonib.backends.dns import ProxyDNSServer
from oonib.backends.daphn3 import Daphn3Server

config = Storage()
config.main = Config('main', 'oonibackend.conf')
config.daphn3 = Config('daphn3', 'oonibackend.conf')

# This tells twisted to set the
server.version = "Apache"

application = service.Application('oonibackend')
serviceCollection = service.IServiceCollection(application)
internet.TCPServer(int(config.main.http_port), server.Site(HTTPBackend())).setServiceParent(serviceCollection)

# Start the DNS Server related services
TCPDNSServer = ProxyDNSServer()
internet.TCPServer(int(config.main.dns_tcp_port), TCPDNSServer).setServiceParent(serviceCollection)
UDPFactory = dns.DNSDatagramProtocol(TCPDNSServer)
internet.UDPServer(int(config.main.dns_udp_port), UDPFactory).setServiceParent(serviceCollection)

# Start the ooni backend thing
daphn3 = Daphn3Server()
internet.TCPServer(int(config.main.daphn3_port), daphn3).setServiceParent(serviceCollection)

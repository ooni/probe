"""
    ooni backend
    ************

    This is the backend system responsible for running certain services that
    are useful for censorship detection.
"""
import json
import random
import string

from twisted.application import internet

from twisted.internet import protocol, reactor, defer
from twisted.application import internet, service
from twisted.application.service import Application

from twisted.web import resource, server, static
from twisted.web.microdom import escape
from twisted.protocols import basic
from twisted.names import dns

from ooni.utils import log

from oonib.report.api import reportingBackend
from oonib.lib.ssl import SSLContext
from oonib import config

from oonib.testhelpers.httph import HTTPReturnJSONHeadersHelper
from oonib.testhelpers.dns import ProxyDNSServer
#from oonib.testhelpers.daphn3 import Daphn3Server

from cyclone import web

# This tells twisted to set the
server.version = config.main.server_version

application = service.Application('oonibackend')
serviceCollection = service.IServiceCollection(application)

if config.main.ssl_port:
    internet.SSLServer(int(config.main.ssl_port),
                   server.Site(HTTPBackend()),
                   SSLContext(config),
                  ).setServiceParent(serviceCollection)

# Start the DNS Server related services
if config.main.dns_tcp_port:
    TCPDNSServer = ProxyDNSServer()
    internet.TCPServer(int(config.main.dns_tcp_port),
                       TCPDNSServer).setServiceParent(serviceCollection)

if config.main.dns_udp_port:
    UDPFactory = dns.DNSDatagramProtocol(TCPDNSServer)
    internet.UDPServer(int(config.main.dns_udp_port),
                       UDPFactory).setServiceParent(serviceCollection)

# XXX this needs to be ported
# Start the OONI daphn3 backend
#if config.main.daphn3_port:
#    daphn3 = Daphn3Server()
#    internet.TCPServer(int(config.main.daphn3_port),
#                       daphn3).setServiceParent(serviceCollection)

if config.main.reporting_port:
    internet.TCPServer(int(config.main.reporting_port),
                       reportingBackend).setServiceParent(serviceCollection)

if config.helpers.http_return_request_port:
    internet.TCPServer(int(config.helpers.http_return_request_port),
            HTTPReturnJSONHeadersHelper).setServiceParent(serviceCollection)


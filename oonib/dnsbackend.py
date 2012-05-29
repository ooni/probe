from twisted.internet.protocol import Factory, Protocol
from twisted.internet import reactor
from twisted.names import dns
from twisted.names import client, server

class ProxyDNSServer(server.DNSServerFactory):
    def __init__(self, authorities = None,
                 caches = None, clients = None,
                 verbose = 0):
        resolver = client.Resolver(servers=[('8.8.8.8', 53)])
        server.DNSServerFactory.__init__(self, authorities = authorities,
                                         caches = caches, clients = [resolver],
                                         verbose = verbose)
    def handleQuery(self, message, protocol, address):
        print message, protocol, address
        server.DNSServerFactory.handleQuery(self, message, protocol, address)

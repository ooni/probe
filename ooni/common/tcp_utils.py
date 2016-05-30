from twisted.internet.protocol import Factory, Protocol

class TCPConnectProtocol(Protocol):
    def connectionMade(self):
        self.transport.loseConnection()

class TCPConnectFactory(Factory):
    noisy = False
    def buildProtocol(self, addr):
        return TCPConnectProtocol()

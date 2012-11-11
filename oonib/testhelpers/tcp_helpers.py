from twisted.internet.protocol import Protocol, Factory

class TCPEchoProtocol(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

class TCPEchoHelper(Factory):
    """
    A very simple echo protocol implementation
    """
    protocol = TCPEchoProtocol




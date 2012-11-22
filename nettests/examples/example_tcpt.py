from ooni.templates import tcpt

class ExampleTCPT(tcpt.TCPTest):
    def test_hello_world(self):
        self.address = "127.0.0.1"
        self.port = 57002
        payload = "Hello World!\n\r"
        return self.sendPayload(payload)

from twisted.internet import defer
from ooni import nettest

class MyIP(nettest.NetTestCase):
    def test_simple(self):
        self.report['foobar'] = 'antani'
        return defer.succeed(42)

    def postProcessor(self, measurements):
        print measurements
        self.report['antani'] = 'testing'

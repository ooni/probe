import random
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.utils import log
from ooni.protocols.scapyproto import ScapyTest

from ooni.lib.txscapy import txsr, txsend

class scapyArgs(usage.Options):
    optParameters = []

class ExampleScapyTest(ScapyTest):
    """
    An example of writing a scapy Test
    """
    implements(IPlugin, ITest)

    shortName = "example_scapy"
    description = "An example of a scapy test"
    requirements = None
    options = scapyArgs
    blocking = False

    receive = True
    pcapfile = 'example_scapy.pcap'
    def initialize(self, reactor=None):
        if not self.reactor:
            from twisted.internet import reactor
            self.reactor = reactor

        self.request = {}
        self.response = {}

    def build_packets(self):
        """
        Override this method to build scapy packets.
        """
        from scapy.all import IP, TCP
        return IP()/TCP()

    def load_assets(self):
        return {}

examplescapy = ExampleScapyTest(None, None, None)


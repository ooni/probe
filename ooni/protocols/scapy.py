import random
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.utils import log

from ooni.lib.txscapy import txsr, txsend

class ScapyTest(OONITest):
    """
    A utility class for writing scapy driven OONI tests.
    """

    receive = True
    timeout = None
    pcapfile = 'scapytest.pcap'
    def initialize(self, reactor=None):

        if not self.reactor:
            from twisted.internet import reactor
            self.reactor = reactor

        self.request = {}
        self.response = {}

    def experiment(self, args):
        log.msg("Running experiment")
        if self.receive:
            log.msg("Sending and receiving packets.")
            d = txsr(self.build_packets(), pcapfile=self.pcapfile,
                    timeout=self.timeout)
        else:
            log.msg("Sending packets.")
            d = txsend(self.build_packets())

        def finished(data):
            log.msg("Finished sending")
            return data

        d.addCallback(finished)
        return d

    def build_packets(self):
        """
        Override this method to build scapy packets.
        """
        from scapy.all import IP, TCP
        return IP()/TCP()

    def load_assets(self):
        return {}


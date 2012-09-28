# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer

from ooni.nettest import TestCase
from ooni.utils import log

from ooni.lib.txscapy import txsr, txsend

from scapy.all import *
class ScapyTest(TestCase):
    """
    A utility class for writing scapy driven OONI tests.

    * pcapfile: specify where to store the logged pcapfile

    * timeout: timeout in ms of when we should stop waiting to receive packets

    * receive: if we should also receive packets and not just send
    """

    receive = True
    timeout = None
    pcapfile = 'scapytest.pcap'
    input = IP()/TCP()
    def setUp(self):

        if not self.reactor:
            from twisted.internet import reactor
            self.reactor = reactor

        self.request = {}
        self.response = {}

    def test_sendReceive(self):
        log.msg("Running send receive")
        if self.receive:
            log.msg("Sending and receiving packets.")
            d = txsr(self.buildPackets(), pcapfile=self.pcapfile,
                    timeout=self.timeout)
        else:
            log.msg("Sending packets.")
            d = txsend(self.buildPackets())

        def finished(data):
            log.msg("Finished sending")
            return data

        d.addCallback(finished)
        return d

    def buildPackets(self):
        """
        Override this method to build scapy packets.
        """
        return self.input



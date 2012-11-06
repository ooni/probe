# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer, threads

from scapy.all import IP, TCP, send, sr

from ooni.nettest import NetTestCase
from ooni.utils import log

from ooni.lib.txscapy import TXScapy

class ScapyTest(NetTestCase):
    """
    A utility class for writing scapy driven OONI tests.

    * pcapfile: specify where to store the logged pcapfile

    * timeout: timeout in ms of when we should stop waiting to receive packets

    * receive: if we should also receive packets and not just send
    """
    name = "Scapy Test"
    version = 0.1

    receive = True
    timeout = 1
    pcapfile = 'packet_capture.pcap'
    packet = IP()/TCP()
    reactor = None

    answered = None
    unanswered = None


    def setUp(self):
        if not self.reactor:
            from twisted.internet import reactor
            self.reactor = reactor
        self.questions = []
        self.answers = []
        self.processInputs()

    def processInputs(self):
        """
        Place here the logic for validating and processing of inputs and
        command line arguments.
        """
        pass

    def tearDown(self):
        log.debug("Tearing down reactor")

    def finished(self, *arg):
        log.debug("Calling final close")

        self.questions = self.txscapy.questions
        self.answers = self.txscapy.answers

        log.debug("These are the questions: %s" % self.questions)
        log.debug("These are the answers: %s" % self.answers)

        self.txscapy.finalClose()

    def sendReceivePackets(self):
        packets = self.buildPackets()

        log.debug("Sending and receiving %s" % packets)

        self.txscapy = TXScapy(packets, pcapfile=self.pcapfile,
                          timeout=self.timeout, reactor=self.reactor)

        self.txscapy.sr(packets, pcapfile=self.pcapfile,
                 timeout=self.timeout, reactor=self.reactor)

        d = self.txscapy.deferred
        d.addCallback(self.finished)

        return d

    def sendPackets(self):
        log.debug("Sending and receiving of packets %s" % packets)

        packets = self.buildPackets()

        self.txscapy = TXScapy(packets, pcapfile=self.pcapfile,
                          timeout=self.timeout, reactor=self.reactor)

        self.txscapy.send(packets, reactor=self.reactor).deferred

        d = self.txscapy.deferred
        d.addCallback(self.finished)

        return d

    def buildPackets(self):
        """
        Override this method to build scapy packets.
        """
        pass

class BlockingScapyTest(ScapyTest):
    """
    This is a very basic Scapy Test template that does not do all the
    multithreading kung-fu of txscapy, but maintains the same API.

    This will allow tests implemented using the BlockingScapyTest API to easily
    migrate to the new API.
    """
    name = "Blocking Scapy Test"
    version = 0.1

    timeout = None

    answered = None
    unanswered = None

    def sendReceivePackets(self):
        packets = self.buildPackets()

        log.debug("Sending and receiving %s" % packets)

        self.answered, self.unanswered = sr(packets, timeout=self.timeout)

        log.debug("%s %s" % (ans, unans))

    def sendPackets(self):
        packets = self.buildPackets()

        log.debug("Sending packets %s" % packets)

        send(packets)


    def buildPackets(self):
        """
        Override this method to build scapy packets.
        """
        pass


# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer, threads

from scapy.all import send, sr, IP, TCP

from ooni.nettest import NetTestCase
from ooni.utils import log

from ooni.lib.txscapy import TXScapy

def createPacketReport(packet_list):
    """
    Takes as input a packet a list containing a dict with the packet
    summary and the raw packet.
    """
    report = []
    for packet in packet_list:
        report.append({'raw_packet': str(packet),
            'summary': str(packet.summary())})
    return report

class BaseScapyTest(NetTestCase):
    """
    The report of a test run with scapy looks like this:

    report:
        sent_packets: [{'raw_packet': BASE64Encoding of packet,
                        'summary': 'IP / TCP 192.168.2.66:ftp_data > 8.8.8.8:http S']
        answered_packets: []

    """
    name = "Base Scapy Test"
    version = 0.1

    requiresRoot = True

    sentPackets = []
    answeredPackets = []

    def sr(self, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.sr for sending and receiving of packets
        at layer 3.
        """
        answered_packets, sent_packets = sr(*arg, **kw)
        self.report['answered_packets'] = createPacketReport(answered_packets)
        self.report['sent_packets'] = createPacketReport(sent_packets)
        return (answered_packets, sent_packets)

    def send(self, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.send for sending of packets at layer 3
        """
        sent_packets = send(*arg, **kw)
        self.report['sent_packets'] = createPacketReport(sent_packets)
        return sent_packets

class TXScapyTest(BaseScapyTest):
    """
    A utility class for writing scapy driven OONI tests.

    * pcapfile: specify where to store the logged pcapfile

    * timeout: timeout in ms of when we should stop waiting to receive packets

    * receive: if we should also receive packets and not just send

    XXX This is currently not working
    """
    name = "TX Scapy Test"
    version = 0.1

    receive = True
    timeout = 1
    pcapfile = 'packet_capture.pcap'
    packet = IP()/TCP()
    reactor = None

    answered = None
    unanswered = None

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


# -*- coding: utf-8 -*-

'''
 scapyt.py
 ---------
 Template for a NetTestCase that works with packets and scapy.

 @authors: Isis Lovecruft, Arturo Filasto
 @license: see included LICENSE file
 @copyright: Isis Lovecruft, Arturo Filasto, The Tor Project Inc.
 @version: 0.0.9-alpha
'''

import random
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer, threads

from scapy.all import send, sr, IP, TCP, config

from ooni.reporter import createPacketReport
from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni import config

from ooni.utils.txscapy import ScapySender, getDefaultIface, ScapyFactory

class BaseScapyTest(NetTestCase):
    """
    The report of a test run with scapy looks like this:

    report:
        sent_packets: [{
            'raw_packet': BASE64Encoding of packet,
            'summary': 'IP / TCP 192.168.2.66:ftp_data > 8.8.8.8:http S'}]
        answered_packets: []
    """
    name = "Base Scapy Test"
    version = 0.2
    requiresRoot = True

    baseFlags = [
        ['ipsrc', 's', False,
         'Check if IP src and ICMP IP citation match when processing answers'],
        ['seqack', 'k', False,
         'Check if TCP sequence number and ACK match in the ICMP citation'],
        ['ipid', 'i', False,
         'Check if the IPID matches when processing answers']]

    def _setUp(self):
        self.report['answer_flags'] = []
        self.report['sent_packets'] = []
        self.report['answered_packets'] = []

        if not config.scapyFactory:
            log.debug("Scapy factoring not set, registering it.")
            config.scapyFactory = ScapyFactory(config.advanced.interface)

        if self.localOptions:
            for check in ['checkIPsrc', 'checkIPID', 'checkSeqACK']:
                if not hasattr(config, check):
                    config.checkIPsrc = self.localOptions['ipsrc']
                    config.checkIPID = self.localOptions['ipid']
                    config.checkSeqACK = self.localOptions['seqack']

        # XXX we don't support strict matching since (from scapy's
        # documentation), some stacks have a bug for which the bytes in the
        # IPID are swapped.  Perhaps in the future we will want to have more
        # fine grained control over this.
        if config.checkIPsrc:
            self.report['answer_flags'].append('ipsrc')
        if config.checkIPID:
            self.report['answer_flags'].append('ipid')
        if config.checkSeqACK:
            self.report['answer_flags'].append('seqack')

    def finishedSendReceive(self, packets):
        """
        This gets called when all packets have been sent and received.
        """
        answered, unanswered = packets

        for snd, rcv in answered:
            log.debug("Writing report for scapy test")
            sent_packet = snd
            received_packet = rcv

            if not config.privacy.includeip:
                log.msg("Detected you would like to exclude your IP from the report")
                log.msg("Stripping source and destination IPs from the reports")
                sent_packet.src = '127.0.0.1'
                received_packet.dst = '127.0.0.1'

            self.report['sent_packets'].append(sent_packet)
            self.report['answered_packets'].append(received_packet)
        return packets

    def processPacket(self, packet):
        """Hook to process packets as they arrive."""

    def sr(self, packets, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.sr for sending and receiving of packets
        at layer 3.
        """
        scapySender = ScapySender()
        scapySender.processPacket = self.processPacket
        config.scapyFactory.registerProtocol(scapySender)
        log.debug("Using sending with hash %s" % scapySender.__hash__)

        d = scapySender.startSending(packets)
        d.addCallback(self.finishedSendReceive)
        return d

    def sr1(self, packets, *arg, **kw):
        def done(packets):
            """
            We do this so that the returned value is only the one packet that
            we expected a response for, identical to the scapy implementation
            of sr1.
            """
            try:
                return packets[0][0][1]
            except IndexError:
                log.err("Got no response...")
                return packets

        scapySender = ScapySender()
        scapySender.expected_answers = 1
        scapySender.processPacket = self.processPacket
        config.scapyFactory.registerProtocol(scapySender)

        log.debug("Running sr1")
        d = scapySender.startSending(packets)
        log.debug("Started to send")
        d.addCallback(self.finishedSendReceive)
        d.addCallback(done)
        return d

    def send(self, packets, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.send for sending packets at layer 3.
        """
        scapySender = ScapySender()
        scapySender.processPacket = self.processPacket
        config.scapyFactory.registerProtocol(scapySender)
        scapySender.sendPackets(packets)

        scapySender.stopSending()
        for packet in packets:
            self.reportSentPacket(packet)

ScapyTest = BaseScapyTest

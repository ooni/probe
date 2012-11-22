# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import random
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer, threads

from scapy.all import send, sr, IP, TCP, config

from ooni.nettest import NetTestCase
from ooni.utils import log

from ooni import config

from ooni.utils.txscapy import ScapyProtocol

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
    baseFlags = [
            ['ipsrc', 's', 'Does *not* check if IP src and ICMP IP citation matches when processing answers'],
            ['seqack', 'k', 'Check if TCP sequence number and ack matches when processing answers'],
            ['ipid', 'i', 'Check if IP id matches when processing answers']
            ]

    def _setUp(self):
        self.report['answer_flags'] = []
        if self.localOptions['ipsrc']:
            config.checkIPsrc = 0
        else:
            self.report['answer_flags'].append('ipsrc')
            config.checkIPsrc = 1

        if self.localOptions['ipid']:
            self.report['answer_flags'].append('ipid')
            config.checkIPID = 1
        else:
            config.checkIPID = 0
        # XXX we don't support strict matching

        if self.localOptions['seqack']:
            self.report['answer_flags'].append('seqack')
            config.check_TCPerror_seqack = 1
        else:
            config.check_TCPerror_seqack = 0

    def sr(self, packets, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.sr for sending and receiving of packets
        at layer 3.
        """
        def finished(packets):
            answered, unanswered = packets
            self.report['answered_packets'] = []
            self.report['sent_packets'] = []
            for snd, rcv in answered:
                log.debug("Writing report for scapy test")
                sent_packet = snd
                received_packet = rcv

                if not config.privacy.includeip:
                    log.msg("Detected you would not like to include your ip in the report")
                    log.msg("Stripping source and destination IPs from the reports")
                    sent_packet.src = '127.0.0.1'
                    received_packet.dst = '127.0.0.1'

                pkt_report_r = createPacketReport(received_packet)
                pkt_report_s = createPacketReport(sent_packet)
                self.report['answered_packets'].append(pkt_report_r)
                self.report['sent_packets'].append(pkt_report_s)
                log.debug("Done")
            return packets

        scapyProtocol = ScapyProtocol(*arg, **kw)
        d = scapyProtocol.startSending(packets)
        d.addCallback(finished)
        return d

    def send(self, pkts, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.send for sending of packets at layer 3
        """
        raise Exception("Not implemented")



# -*- coding:utf8 -*-
# txscapy
# *******
# Here shall go functions related to using scapy with twisted.
#
# This software has been written to be part of OONI, the Open Observatory of
# Network Interference. More information on that here: http://ooni.nu/

import struct
import socket
import os
import sys
import time

from twisted.internet import protocol, base, fdesc
from twisted.internet import reactor, threads, error
from twisted.internet import defer, abstract
from zope.interface import implements

from scapy.config import conf

from ooni.utils import log
from ooni import config

try:
    conf.use_pcap = True
    conf.use_dnet = True

    from scapy.all import PcapWriter
    from scapy.arch import pcapdnet

    config.pcap_dnet = True

except ImportError, e:
    log.err("pypcap or dnet not installed. Certain tests may not work.")
    config.pcap_dnet = False
    conf.use_pcap = False
    conf.use_dnet = False

    from scapy.all import PcapWriter

from scapy.all import BasePacketList, conf, PcapReader
from scapy.all import conf, Gen, SetGen, MTU

def getNetworksFromRoutes():
    from scapy.all import conf, ltoa, read_routes
    from ipaddr    import IPNetwork, IPAddress

    ## Hide the 'no routes' warnings
    conf.verb = 0

    networks = []
    for nw, nm, gw, iface, addr in read_routes():
        n = IPNetwork( ltoa(nw) )
        (n.netmask, n.gateway, n.ipaddr) = [IPAddress(x) for x in [nm, gw, addr]]
        n.iface = iface
        if not n.compressed in networks:
            networks.append(n)

    return networks

def getDefaultIface():
    networks = getNetworksFromRoutes()
    for net in networks:
        if net.is_private:
            return net.iface
    raise IfaceError

class TXPcapWriter(PcapWriter):
    def __init__(self, *arg, **kw):
        PcapWriter.__init__(self, *arg, **kw)
        fdesc.setNonBlocking(self.f)

class ScapyProtocol(abstract.FileDescriptor):
    def __init__(self, interface, super_socket=None, timeout=5):
        abstract.FileDescriptor.__init__(self, reactor)
        if not super_socket:
            super_socket = conf.L3socket(iface=interface, promisc=True, filter='')
            #super_socket = conf.L2socket(iface=interface)

        fdesc._setCloseOnExec(super_socket.ins.fileno())
        self.super_socket = super_socket

        self.interface = interface
        self.timeout = timeout

        # This dict is used to store the unique hashes that allow scapy to
        # match up request with answer
        self.hr_sent_packets = {}

        # These are the packets we have received as answer to the ones we sent
        self.answered_packets = []

        # These are the packets we send
        self.sent_packets = []

        # This deferred will fire when we have finished sending a receiving packets.
        self.d = defer.Deferred()
        # Should we look for multiple answers for the same sent packet?
        self.multi = False

        # When 0 we stop when all the packets we have sent have received an
        # answer
        self.expected_answers = 0

    def fileno(self):
        return self.super_socket.ins.fileno()

    def processPacket(self, packet):
        """
        Hook useful for processing packets as they come in.
        """

    def processAnswer(self, packet, answer_hr):
        log.debug("Got a packet from %s" % packet.src)
        log.debug("%s" % self.__hash__)
        for i in range(len(answer_hr)):
            if packet.answers(answer_hr[i]):
                self.answered_packets.append((answer_hr[i], packet))
                if not self.multi:
                    del(answer_hr[i])
                break

        if len(self.answered_packets) == len(self.sent_packets):
            log.debug("All of our questions have been answered.")
            self.stopSending()
            return

        if self.expected_answers and \
                self.expected_answers == len(self.answered_packets):
            log.debug("Got the number of expected answers")
            self.stopSending()

    def doRead(self):
        timeout = time.time() - self._start_time
        if self.timeout and time.time() - self._start_time > self.timeout:
            self.stopSending()
        packet = self.super_socket.recv(MTU)
        if packet:
            self.processPacket(packet)
            # A string that has the same value for the request than for the
            # response.
            hr = packet.hashret()
            if hr in self.hr_sent_packets:
                answer_hr = self.hr_sent_packets[hr]
                self.processAnswer(packet, answer_hr)

    def stopSending(self):
        self.stopReading()
        self.super_socket.close()
        if hasattr(self, "d"):
            result = (self.answered_packets, self.sent_packets)
            self.d.callback(result)
            del self.d

    def write(self, packet):
        """
        Write a scapy packet to the wire.
        """
        return self.super_socket.send(packet)

    def sendPackets(self, packets):
        if not isinstance(packets, Gen):
            packets = SetGen(packets)
        for packet in packets:
            hashret = packet.hashret()
            if hashret in self.hr_sent_packets:
                self.hr_sent_packets[hashret].append(packet)
            else:
                self.hr_sent_packets[hashret] = [packet]
            self.sent_packets.append(packet)
            self.write(packet)

    def startSending(self, packets):
        self._start_time = time.time()
        self.startReading()
        self.sendPackets(packets)
        return self.d



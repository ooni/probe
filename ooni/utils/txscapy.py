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


from scapy.all import PcapWriter, MTU
from scapy.all import BasePacketList, conf, PcapReader

from scapy.all import conf, Gen, SetGen

from ooni.utils import log

class TXPcapWriter(PcapWriter):
    def __init__(self, *arg, **kw):
        PcapWriter.__init__(self, *arg, **kw)
        fdesc.setNonBlocking(self.f)

class ScapyProtocol(abstract.FileDescriptor):
    def __init__(self, super_socket=None, 
            reactor=None, timeout=None, receive=True):
        abstract.FileDescriptor.__init__(self, reactor)
        # By default we use the conf.L3socket
        if not super_socket:
            super_socket = conf.L3socket()
        self.super_socket = super_socket

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
        self.debug = False
        self.multi = False
        # XXX this needs to be implemented. It would involve keeping track of
        # the state of the sending via the super socket file descriptor and
        # firing the callback when we have concluded sending. Check out
        # twisted.internet.udp to see how this is done.
        self.receive = receive

    def fileno(self):
        return self.super_socket.ins.fileno()

    def processPacket(self, packet):
        """
        Hook useful for processing packets as they come in.
        """

    def processAnswer(self, packet, answer_hr):
        log.debug("Got a packet from %s" % packet.src)
        for i in range(len(answer_hr)):
            if packet.answers(answer_hr[i]):
                self.answered_packets.append((answer_hr[i], packet))
                if not self.multi:
                    del(answer_hr[i])
                break
        if len(self.answered_packets) == len(self.sent_packets):
            # All of our questions have been answered.
            self.stopSending()

    def doRead(self):
        timeout = time.time() - self._start_time
        if self.timeout and time.time() - self._start_time > self.timeout:
            self.stopSending()
        packet = self.super_socket.recv()
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
        Write a scapy packet to the wire
        """
        hashret = packet.hashret()
        if hashret in self.hr_sent_packets:
            self.hr_sent_packets[hashret].append(packet)
        else:
            self.hr_sent_packets[hashret] = [packet]
        self.sent_packets.append(packet)
        return self.super_socket.send(packet)

    def sendPackets(self, packets):
        if not isinstance(packets, Gen):
            packets = SetGen(packets)
        for packet in packets:
            self.write(packet)

    def startSending(self, packets):
        self._start_time = time.time()
        self.startReading()
        self.sendPackets(packets)
        return self.d

def sr(x, filter=None, iface=None, nofilter=0, timeout=None):
    super_socket = conf.L3socket(filter=filter, iface=iface, nofilter=nofilter)
    sp = ScapyProtocol(super_socket=super_socket, timeout=timeout)
    return sp.startSending(x)

def send(x, filter=None, iface=None, nofilter=0, timeout=None):
    super_socket = conf.L3socket(filter=filter, iface=iface, nofilter=nofilter)
    sp = ScapyProtocol(super_socket=super_socket, timeout=timeout)
    return sp.startSending(x)



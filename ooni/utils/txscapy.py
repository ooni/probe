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

from twisted.internet import protocol, base, fdesc, error, defer
from twisted.internet import reactor, threads
from zope.interface import implements

from scapy.all import Gen
from scapy.all import SetGen

from ooni.utils import log

from scapy.all import PcapWriter, MTU
from scapy.all import BasePacketList, conf, PcapReader

class TXPcapWriter(PcapWriter):
    def __init__(self, *arg, **kw):
        PcapWriter.__init__(self, *arg, **kw)
        fdesc.setNonBlocking(self.f)

def txSniff(count=0, store=1, offline=None, 
        prn = None, lfilter=None,
        L2socket=None, timeout=None, 
        opened_socket=None, stop_filter=None,
        *arg, **karg):
    """
    XXX we probably want to rewrite the scapy sniff function to better suite our needs.
    """


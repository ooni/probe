#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  +---------+
#  | echo.py |
#  +---------+
#     A simple ICMP-8 ping test.
#
# @authors: Isis Lovecruft, <isis@torproject.org>
# @version: 0.0.2-pre-alpha
# @license: copyright (c) 2012 Isis Lovecruft
#           see attached LICENCE file
#

import os
import sys

from twisted.python   import usage
from twisted.internet import reactor, defer
from ooni             import nettest
from ooni.utils       import log, net, Storage, txscapy

try:
    from scapy.all             import IP, ICMP
    from scapy.all             import sr1
    from ooni.lib              import txscapy
    from ooni.lib.txscapy      import txsr, txsend
    from ooni.templates.scapyt import BaseScapyTest
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")

class UsageOptions(usage.Options):
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['file', 'f', None, 'File of list of IPs to ping'],
        ['interface', 'i', None, 'Network interface to use'],
        ['count', 'c', 1, 'Number of packets to send', int],
        ['size', 's', 56, 'Number of bytes to send in ICMP data field', int],
        ['ttl', 'l', 25, 'Set the IP Time to Live', int],
        ['timeout', 't', 2, 'Seconds until timeout if no response', int],
        ['pcap', 'p', None, 'Save pcap to this file'],
        ['receive', 'r', True, 'Receive response packets']]

class EchoTest(nettest.NetTestCase):
    """
    xxx fill me in
    """
    name         = 'echo'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A simple ping test to see if a host is reachable.'
    version      = '0.0.2'
    requiresRoot = True

    usageOptions    = UsageOptions
    #requiredOptions = ['dst']

    def setUp(self, *a, **kw):
        self.destinations = {}

        if self.localOptions:
            for key, value in self.localOptions.items():
                log.debug("setting self.%s = %s" % (key, value))
                setattr(self, key, value)

        self.timeout *= 1000            ## convert to milliseconds

        if not self.interface:
            try:
                iface = txscapy.getDefaultIface()
            except Exception, e:
                log.msg("No network interface specified!")
                log.err(e)
            else:
                log.msg("Using system default interface: %s" % iface)
                self.interface = iface

        if self.pcap:
            try:
                self.pcapfile = open(self.pcap, 'a+')
            except:
                log.msg("Unable to write to pcap file %s" % self.pcap)
            else:
                self.pcap = net.capturePacket(self.pcapfile)

        if not self.dst:
            if self.file:
                self.dstProcessor(self.file)
                for key, value in self.destinations.items():
                    for label, data in value.items():
                        if not 'ans' in data:
                            self.dst = label
        else:
            self.addDest(self.dst)
        log.debug("self.dst is now: %s" % self.dst)

        log.debug("Initialization of %s test completed." % self.name)

    def addDest(self, dest):
        d = dest.strip()
        self.destinations[d] = {'dst_ip': d}

    def dstProcessor(self, inputfile):
        from ipaddr import IPAddress

        if os.path.isfile(inputfile):
            with open(inputfile) as f:
                for line in f.readlines():
                    if line.startswith('#'):
                        continue
                    self.addDest(line)

    def test_icmp(self):
        def process_response(echo_reply, dest):
           ans, unans = echo_reply
           if ans:
               log.msg("Recieved echo reply from %s: %s" % (dest, ans))
           else:
               log.msg("No reply was received from %s. Possible censorship event." % dest)
               log.debug("Unanswered packets: %s" % unans)
           self.report[dest] = echo_reply

        for label, data in self.destinations.items():
            reply = sr1(IP(dst=lebal)/ICMP())
            process = process_reponse(reply, label)

        #(ans, unans) = ping
        #self.destinations[self.dst].update({'ans': ans,
        #                                    'unans': unans,
        #                                    'response_packet': ping})
        #return ping

        #return reply

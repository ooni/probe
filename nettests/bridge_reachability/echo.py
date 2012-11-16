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
from ooni.nettest     import NetTestCase
from ooni.utils       import log, net, Storage

try:
    from scapy.all        import IP, ICMP
    from scapy.all        import sr1
    from ooni.lib         import txscapy
    from ooni.lib.txscapy import txsr, txsend
    from ooni.templates.scapyt   import BaseScapyTest
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

class EchoTest(BaseScapyTest):
    """
    Basic ping test. This takes an input file containing one IP or hostname
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
                iface = net.getDefaultIface()
            except Exception, e:
                log.msg("No network interface specified!")
                log.exception(e)
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
                for address, details in self.destinations.items():
                    for labels, data in details.items():
                        if not 'ans' in labels:
                            self.dst = details['dst_ip']
        else:
            self.addDest(self.dst)
        log.debug("self.dst is now: %s" % self.dst)

        log.debug("Initialization of %s test completed." % self.name)

    def addDest(self, dest):
        d = dest.strip()
        self.destinations[d] = {'dst_ip': d}

    def dstProcessor(self, inputfile):
        if os.path.isfile(inputfile):
            with open(inputfile) as f:
                for line in f.readlines():
                    if line.startswith('#'):
                        continue
                    self.addDest(line)

    def test_icmp(self):

        def process_response(pkt, dest):
            try:
                ans, unans = pkt
                if ans:
                    log.msg("Recieved echo-reply: %s" % pkt.summary())
                    self.destinations[dest]['ans'] = a.show2()
                    self.report['response'] = [a.show2() for a in ans]
                    self.report['censored'] = False
                else:
                    log.msg("No reply from %s. Possible censorship event." % dest)
                    log.debug("Unanswered packets: %s" % unans.summary())
                    self.report['response'] = [u.show2() for u in unans]
                    self.report['censored'] = True
            except Exception, e:
                log.exception(e)

        try:
            for dest, data in self.destinations.items():
                reply = txsr(IP(dst=dest)/ICMP(),
                           iface=self.interface,
                           retry=self.count,
                           multi=True,
                           timeout=self.timeout)
                process = process_response(reply, dest)
        except Exception, e:
            log.exception(e)

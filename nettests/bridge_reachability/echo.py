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
from twisted.internet import reactor, defer, address
from ooni             import nettest
from ooni.utils       import log, net, Storage

try:
    from scapy.all          import IP, ICMP
    from scapy.all          import sr1
    from ooni.utils         import txscapy
except Exception, e:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")
    log.exception(e)

class UsageOptions(usage.Options):
    """
    Options for EchoTest.

    Note: 'count', 'size', and 'ttl' have yet to be implemented.
    """
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['file', 'f', None, 'File of list of IPs to ping'],
        ['pcap', 'p', None, 'Save pcap to this file'],
        ['interface', 'i', None, 'Network interface to use'],
        ['receive', 'r', True, 'Receive response packets'],
        ['timeout', 't', 2, 'Seconds to wait if no response', int],
        ['count', 'c', 1, 'Number of packets to send', int],
        ['size', 's', 56, 'Bytes to send in ICMP data field', int],
        ['ttl', 'l', 25, 'Set the IP Time to Live', int]]

class EchoTest(nettest.NetTestCase):
    """
    Basic ping test. This takes an input file containing one IP or hostname
    per line.
    """
    name         = 'echo'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A simple ping test to see if a host is reachable.'
    version      = '0.0.2'
    requiresRoot = True

    usageOptions    = UsageOptions
    #requiredOptions = ['dst']

    def setUp(self, *a, **kw):
        """
        Send an ICMP-8 packet to a host IP, and process the response.

        @param timeout:
            Seconds after sending the last packet to timeout.
        @param interface:
            The interface to restrict listening to.
        @param dst:
            A single host to ping.
        @param file:
            A file of hosts to ping, one per line.
        @param receive:
            Whether or not to receive replies. Defaults to True.
        @param pcap:
            The file to save packet captures to.
        """
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
                        if not 'response' in labels:
                            self.dst = details['dst_ip']
        else:
            self.addDest(self.dst)

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

    def build_packets(self):
        """
        Construct a list of packets to send out.
        """
        packets = []
        for dest, data in self.destinations.items():
            pkt = IP(dst=dest)/ICMP()
            packets.append(pkt)
            ## XXX if a domain was specified, we need a way to check that
            ## its IP matches the one we're seeing in pkt.src
            #try:
            #    address.IPAddress(dest)
            #except:
            #    data['dst_ip'] = pkt.dst
        return packets

    def test_icmp(self):
        """
        Send the list of ICMP packets.

        TODO: add end summary progress report for % answered, etc.
        """
        try:
            def nicely(packets):
                """Print scapy summary nicely."""
                return list([x.summary() for x in packets])

            def process_answered((answered, sent)):
                """Callback function for txscapy.sr()."""
                self.report['sent'] = nicely(sent)
                self.report['answered'] = [nicely(ans) for ans in answered]

                for req, resp in answered:
                    log.msg("Received echo-reply:\n%s" % resp.summary())
                    for dest, data in self.destinations.items():
                        if data['dst_ip'] == resp.src:
                            data['response'] = resp.summary()
                            data['censored'] = False
                    for snd in sent:
                        if snd.dst == resp.src:
                            answered.remove((req, resp))
                return (answered, sent)

            def process_unanswered((unanswered, sent)):
                """
                Callback function for remaining packets and destinations which
                do not have an associated response.
                """
                if len(unanswered) > 0:
                    nicer = [nicely(unans) for unans in unanswered]
                    log.msg("Unanswered/remaining packets:\n%s"
                            % nicer)
                    self.report['unanswered'] = nicer
                for dest, data in self.destinations.items():
                    if not 'response' in data:
                        log.msg("No reply from %s. Possible censorship event."
                                % dest)
                        data['response'] = None
                        data['censored'] = True
                return (unanswered, sent)

            packets = self.build_packets()
            d = txscapy.sr(packets, iface=self.interface, multi=True)
            d.addCallback(process_answered)
            d.addErrback(log.exception)
            d.addCallback(process_unanswered)
            d.addErrback(log.exception)
            self.report['destinations'] = self.destinations
            return d
        except Exception, e:
            log.exception(e)

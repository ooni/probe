#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  +---------+
#  | echo.py |
#  +---------+
#     A simple ICMP-8 ping test.
#
# @authors: Isis Lovecruft, <isis@torproject.org>
# @license: copyright (c) 2012 Isis Lovecruft
#           see attached LICENCE file

import os

from twisted.internet import defer
from twisted.python   import usage
from ooni             import nettest, config
from ooni.utils       import log, net, randomStr

try:
    from scapy.all      import IP, ICMP, sr1
    from ooni.utils     import txscapy
except Exception, e:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")
    log.exception(e)

class EchoOptions(usage.Options):
    """
    Options for EchoTest.
    """
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['receive', 'r', True, 'Receive response packets'],
        ['count', 'c', 1, 'Number of packets to send', int],
        ['icmp_type', 'i', 8, 'ICMP-type to send', int],
        ['payload_size', 'p', 56, 'Bytes to send in ICMP data field', int],
        ['ttl', 't', 25, 'Set the IP Time to Live', int]]

class EchoTest(nettest.NetTestCase):
    """
    Basic ping test. This takes an input file containing one IP or hostname
    per line.
    """
    name         = 'echo'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A simple ping test to see if a host is reachable.'
    version      = '0.0.4'

    requiresRoot = True
    usageOptions = EchoOptions
    inputFile    = ['file', 'f', None, 'File of list of IPs to ping']

    def setUp(self, *a, **kw):
        """
        Send an ICMP-8 packet to a host IP, and process the response.

        @param dst:
            A single host to ping.
        @param file:
            A file of hosts to ping, one per line.
        @param receive:
            Whether or not to receive replies. Defaults to True.
        """
        self.destinations = {}

        if self.localOptions:
            for key, value in self.localOptions.items():
                setattr(self, key, value)

        if hasattr(config.advanced, 'default_timeout'):
            self.timeout = config.advanced.default_timeout
        else:
            self.timeout = 4

        if config.advanced.interface:
            self.interface = config.advanced.interface
        else:
            log.warn("No network interface specified in ooniprobe.conf!")
            try:
                iface = txscapy.getDefaultIface()
            except Exception, ex:
                log.err(ex.message)
            else:
                self.interface = iface
                log.msg("Using system default interface: %s" % iface)

        self.payload = randomStr(self.payload_size)

    def inputProcessor(self, inputfile=None):
        if os.path.isfile(inputfile):
            with open(inputfile) as f:
                for line in f.readlines():
                    if line.startswith('#'):
                        continue
                    yield line.strip().rsplit(':', 1)[0] ## xxx not ipv6 safe

    def icmp_constructor(self, dst=None):
        """Construct a list of ICMP packets to send out."""
        dst_ip = dst if dst is not None else self.input

        packet_list = []
        for x in xrange(self.count):
            p = IP(dst=dst_ip, ttl=self.ttl)/ICMP(type=self.icmp_type)
            p.add_payload(self.payload)
            packet_list.append(p)
        return packet_list

    def test_icmp(self):
        """
        Send the list of ICMP packets.

        TODO: add end summary progress report for % answered, etc.
        """
        def nicely(thing):
            """Log packets prettierly."""
            return [x.summary() for x in thing]

        def process_answered(answered, sent):
            """Callback function for sr()."""

            self.report[self.input] = {}
            self.report[self.input]['answered'] = []
            self.report[self.input]['unanswered'] = []
            self.report[self.input]['sent'] = sent

            if answered:
                for resp in answered:
                    log.msg("Received echo-reply:\n%s" % resp.summary())
                    for snd in sent:
                        if snd.dst == resp.src:
                            answered.remove(resp)
                            self.report[self.input]['answered'].append(resp)
                        else:
                            answered.remove(resp)
                            self.report[self.input]['unanswered'].append(resp)


        log.debug("Building packets...")

        if self.input:
            packets = self.icmp_constructor()
            if self.dst:
                packets.extend(self.icmp_constructor(self.dst))
        else:
            if self.dst:
                packets = self.icmp_constructor(self.dst)

        log.debug("Sending...")
        d = defer.maybeDeferred(sr1, packets, iface=self.interface,
                                timeout=self.timeout, nofilter=1)
        d.addCallbacks(process_answered, log.exception, packets)

        return d

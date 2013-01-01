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
from ooni             import nettest, config, templates
from ooni.utils       import log, net, txscapy, packet, randomStr

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

    Note: 'ttl' has yet to be implemented.
    """
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['file', 'f', None, 'File of list of IPs to ping'],
        ['receive', 'r', True, 'Receive response packets'],
        ['count', 'c', 1, 'Number of packets to send', int],
        ['icmp-type', 'i', 8, 'ICMP-type to send', int],
        ['payload-size', 'p', 56, 'Bytes to send in ICMP data field', int],
        ['ttl', 't', 25, 'Set the IP Time to Live', int]]

class EchoTest(templates.ScapyTest):
    """
    Basic ping test. This takes an input file containing one IP or hostname
    per line.
    """
    name         = 'echo'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A simple ping test to see if a host is reachable.'
    version      = '0.0.2'

    requiresRoot = True
    usageOptions = UsageOptions

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
            self.timeout = 10
        self.timeout *= 1000  ## convert to milliseconds

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

        if not self.dst:
            if self.file:
                self.dstProcessor(self.file)
                for address, details in self.destinations.items():
                    for labels, data in details.items():
                        if not 'response' in labels:
                            self.dst = details['dst']
        else:
            self.addDest(self.dst)

        self.payload = randomStr(self.size)
        self.sender = txscapy.ScapySender()
        self.sender.factory = txscapy.ScapyFactory(self.interface,
                                                   timeout=self.timeout)
        log.debug("Initialization of %s test completed." % self.name)

    def addDest(self, dest):
        d = dest.strip()
        self.destinations[d] = {'dst': d}

    def dstProcessor(self, inputfile):
        if os.path.isfile(inputfile):
            with open(inputfile) as f:
                for line in f.readlines():
                    if line.startswith('#'):
                        continue
                    self.addDest(line)

    @packet.count(self.count)
    @packet.build(self.destinations.get('dst'))
    def icmp_constructor(self, addr):
        """Construct a list of ICMP packets to send out."""
        return IP(dst=addr,
                  ttl=self.ttl)/ICMP(type=self.icmp_type).add_payload(self.payload)

    def test_icmp(self):
        """
        Send the list of ICMP packets.

        TODO: add end summary progress report for % answered, etc.
        """
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
                log.msg("Unanswered/remaining packets:\n%s" % nicer)
                self.report['unanswered'] = nicer
            for dest, data in self.destinations.items():
                if not 'response' in data:
                    log.msg("No reply from %s. Possible censorship event." % dest)
                    data['response'] = None
                    data['censored'] = True
            return (unanswered, sent)

        log.debug("Building packets...")
        packets = self.icmp_constructor()
        log.debug("Sending...")
        d = self.sender.startSending(packets)
        d.addCallbacks(process_answered, log.exception)
        d.addCallbacks(process_unanswered, log.exception)
        self.report['destinations'] = self.destinations
        return d

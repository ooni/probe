#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  +-----------+
#  | tcpsyn.py |
#  +-----------+
#     Send a TCP SYN packet to a test server to check that
#     it is reachable.
#
# @authors: Isis Lovecruft, <isis@torproject.org>
# @version: 0.0.1-pre-alpha
# @license: copyright (c) 2012 Isis Lovecruft
#           see attached LICENCE file
#

import os
import sys

from ipaddr           import IPAddress
from twisted.python   import usage
from twisted.internet import reactor, defer, address
from ooni             import nettest
from ooni.utils       import net, log
from ooni.utils.otime import timestamp

try:
    from scapy.all          import TCP, IP
    from ooni.utils         import txscapy
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")


class UsageOptions(usage.Options):
    """Options for TCPSynTest."""
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['port', 'p', None, 'Host port'],
        ['count', 'c', 3, 'Number of SYN packets to send', int],
        ['interface', 'i', None, 'Network interface to use'],
        ['hexdump', 'x', False, 'Show hexdump of responses'],
        ['pdf', 'y', False,
         'Create pdf of visual representation of packet conversations'],
        ['cerealize', 'z', False,
         'Cerealize scapy objects for further scripting']]

class TCPSynTest(nettest.NetTestCase):
    """
    Sends only a TCP SYN packet to a host IP:PORT, and waits for either a
    SYN/ACK, a RST, or an ICMP error.

    TCPSynTest can take an input file containing one IP:Port pair per line, or
    the commandline switches --dst <IP> and --port <PORT> can be used.
    """
    name         = 'TCP SYN'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A TCP SYN test to see if a host is reachable.'
    version      = '0.0.1'
    requiresRoot = True

    usageOptions = UsageOptions
    inputFile    = ['file', 'f', None, 'File of list of IP:PORTs to ping']

    destinations = {}

    @log.catcher
    def setUp(self, *a, **kw):
        """Configure commandline parameters for TCPSynTest."""
        if self.localOptions:
            for key, value in self.localOptions.items():
                setattr(self, key, value)
        if not self.interface:
            try:
                iface = net.getDefaultIface()
            except net.IfaceError, ie:
                log.msg("Could not find a working network interface!")
            except Exception, ex:
                log.exception(ex)
            else:
                log.msg("Using system default interface: %s" % iface)
                self.interface = iface
        if self.cerealize:
            if True:
                raise NotImplemented("need handler for type(dictproxy)...")
            else:
                from Cerealize import cerealizer
                self.cheerios = Cerealize.cerealizer()
                mind = ['scapy.layers.inet.IP',
                        'scapy.base_classes.Packet_metaclass',
                        'scapy.plist.SndRcvList']
                for spoon in mind:
                    __import__(spoon)
                    self.cheerios.register(spoon)

    def addToDestinations(self, addr, port):
        dst, dport = net.checkIPandPort(addr, port)
        if not dst in self.destinations.keys():
            self.destinations[dst] = {'dst': dst, 'dport': dport}
        else:
            log.debug("XXX Multiple port scanning not yet implemented.")
        return (dst, dport)

    def inputProcessor(self, input_file=None):
        """
        Pull the IPs and PORTs from the commandline options first, and then
        from the input file, and place them in a dict for storing test results
        as they arrive.
        """
        if self.localOptions['dst'] is not None \
                and self.localOptions['port'] is not None:
            log.debug("processing commandline destination input")
            yield self.addToDestinations(self.localOptions['dst'],
                                         self.localOptions['port'])
        if input_file and os.path.isfile(input_file):
            log.debug("processing input file %s" % input_file)
            with open(input_file) as f:
                for line in f.readlines():
                    if line.startswith('#'):
                        continue
                    one = line.strip()
                    raw_ip, raw_port = one.rsplit(':', 1) ## XXX not ipv6 safe!
                    yield self.addToDestinations(raw_ip, raw_port)

    @staticmethod
    def build_packets(addr, port, flags=None, count=3):
        """Construct a list of packets to send out."""
        packets = []
        for x in xrange(count):
            packets.append( IP(dst=addr)/TCP(dport=port, flags=flags) )
        return packets

    @log.catcher
    def test_tcp_syn(self):
        """Send the list of SYN packets."""

        def process_packets(packet_list):
            """xxx"""
            results, unanswered = packet_list

            if self.pdf:
                pdf_name = self.name  +'_'+ timestamp()
                try:
                    results.pdfdump(pdf_name)
                except Exception, ex:
                    log.exception(ex)
                else:
                    log.msg("Visual packet conversation saved to %s.pdf"
                            % pdf_name)

            for (q, r) in results:
                request_data = {'dst': q.dst,
                                'dport': q.dport,
                                'summary': q.summary(),
                                'command': q.command(),
                                'sent_time': q.time}
                response_data = {'summary': r.summary(),
                                 'command': r.command(),
                                 'src': r['IP'].src,
                                 'flags': r['IP'].flags,
                                 'recv_time': r.time,
                                 'delay': r.time - q.time}
                if self.hexdump:
                    request_data.update('hexdump', q.hexdump())
                    response_data.update('hexdump', r.hexdump())
                if self.cerealize:
                    pass

                for dest, data in self.destinations.items():
                    if data['dst'] == response_data['src']:
                        if not 'reachable' in data:
                            if self.hexdump:
                                log.msg("%s\n%s" % (q.hexdump(), r.hexdump()))
                            else:
                                log.msg(" Received response:\n%s ==> %s"
                                        % (q.mysummary(), r.mysummary()))
                            data.update( {'reachable': True,
                                          'request': request_data,
                                          'response': response_data} )
            return unanswered

        def process_unanswered(unanswered):
            """Callback function to process unanswered packets."""
            if unanswered is not None and len(unanswered) > 0:
                log.msg("Waiting on responses from\n%s" %
                        '\n'.join([unans.summary() for unans in unanswered]))
            log.msg("Writing response packet information to report...")
            self.report = (self.destinations)
            return self.destinations

        (addr, port) = self.input
        packets = self.build_packets(addr, port, "S", self.count)
        d = txscapy.sr(packets, iface=self.interface)
        d.addCallbacks(process_packets, log.exception)
        d.addCallbacks(process_unanswered, log.exception)
        return d

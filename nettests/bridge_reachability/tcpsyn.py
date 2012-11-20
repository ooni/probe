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

    def setUp(self, *a, **kw):
        """Configure commandline parameters for TCPSynTest."""
        if self.localOptions:
            for key, value in self.localOptions.items():
                log.debug("setting self.%s = %s" % (key, value))
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
            ## XXX implement multiple port or portrange options
            log.msg("Multiple port scanning not yet implemented.")
        return (dst, dport)

    def inputProcessor(self, input_file=None):
        """
        Pull the IPs and PORTs from the input file, and place them in a dict
        for storing test results as they arrive.
        """
        try:
            ## get the commandline input, if there is one:
            if self.localOptions['dst'] is not None \
                    and self.localOptions['port'] is not None:
                log.debug("processing commandline destination input")
                yield self.addToDestinations(self.localOptions['dst'],
                                             self.localOptions['port'])
            ## get the inputs from inputFile:
            if input_file and os.path.isfile(input_file):
                log.debug("processing input file %s" % input_file)
                with open(input_file) as f:
                    for line in f.readlines():
                        if line.startswith('#'):
                            continue
                        one = line.strip()
                        raw_ip, raw_port = one.rsplit(':', 1) ## XXX not ipv6 safe!
                        yield self.addToDestinations(raw_ip, raw_port)
        except Exception, ex:
            log.exception(ex)

    def test_tcp_syn(self):
        """Send the list of SYN packets."""
        try:
            def build_packets(addr, port):
                """Construct a list of packets to send out."""
                packets = []
                for x in xrange(self.count):
                    pkt = IP(dst=addr)/TCP(dport=port, flags="S")
                    packets.append(pkt)
                return packets

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
                    request_data = {'summary': q.summary(),
                                    'command': q.command(),
                                    'hash': q.hashret(),
                                    'display': q.display(),
                                    'sent_time': q.time}
                    response_data = {'summary': r.summary(),
                                     'command': r.command(),
                                     'hash': r.hashret(),
                                     'src': r['IP'].src,
                                     'flags': r['IP'].flags,
                                     'display': r.display(),
                                     'recv_time': r.time,
                                     'delay': r.time - q.time}
                    if self.hexdump:
                        request_data.update('hexdump', q.hexdump())
                        response_data.update('hexdump', r.hexdump())
                    if self.cerealize:
                        pass
                    result_data = (request_data, response_data)

                    for dest, data in self.destinations.items():
                        if data['dst'] == response_data['src']:
                            if not 'received_response' in data:
                                if self.hexdump:
                                    log.msg("%s" % request.hexdump())
                                    log.msg("%s" % response.hexdump())
                                else:
                                    log.msg("\n    %s\n ==> %s" % (q.summary(),
                                                                   r.summary()))
                                data['result'] = [result_data, ]
                                data['received_response'] = True
                                data['reachable'] = True
                            else:
                                data['result'].append(result_data)

            def process_unanswered(unanswer):
                """Callback function to process unanswered packets."""
                #log.debug("%s" % str(unanswer))
                return unanswer

            (addr, port) = self.input
            packets = build_packets(addr, port)

            results = []

            d = txscapy.sr(packets, iface=self.interface)
            d.addCallbacks(process_packets, log.exception)
            d.addCallbacks(process_unanswered, log.exception)
            self.report['destinations'] = self.destinations
            return d

        except Exception, e:
            log.exception(e)

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

try:
    from scapy.all          import TCP, IP
    from scapy.all          import sr1
    from ooni.utils         import txscapy
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")


class UsageOptions(usage.Options):
    """Options for TCPSynTest."""
    optParameters = [['dst', 'd', None, 'Host IP to ping'],
                     ['port', 'p', None, 'Host port'],
                     ['count', 'c', 3, 'Number of SYN packets to send', int],
                     ['interface', 'i', None, 'Network interface to use'],
                     ['verbose', 'v', False, 'Show hexdump of responses']]

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

    def addToDestinations(self, addr, port):
        try:
            dst, dport = net.checkIPandPort(addr, port)
            if not dst in self.destinations.keys():
                self.destinations[dst] = {'dst': dst, 'dport': dport}
            return (dst, dport)
        except Exception, ex:
            log.exception(ex)

    def inputProcessor(self, input_file=None):
        """
        Pull the IPs and PORTs from the input file, and place them in a dict
        for storing test results as they arrive.
        """
        try:
            ## get the commandline input, if there is one:
            if self.localOptions['dst'] is not None and self.localOptions['port'] is not None:
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
                        raw_ip, raw_port = one.rsplit(':', 1)  ## XXX not ipv6 safe!
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

            def sort_nicely(packets):
                """Print the summary of each packet in a list."""
                return [pkt.summary() for pkt in packets]

            def tcp_flags(responses):
                """Print summary of hosts which responded with a SYN/ACK."""
                for response in responses:
                    layer = response.getlayer('TCP') if response.haslayer('TCP') else None
                    yield layer.sprintf("{TCP:%TCP.flags%}") if layer else None

            def received_syn(responses, flags):
                yield responses.filter(
                    lambda x: (x for x in responses if str(flags) in ['S','SA']))

            def process_packets(packet_list):
                results, unanswered = packet_list

                log.debug("RESULTS ARE: %s" % results)
                log.debug("UNANSWERED: %s" % unanswered)

                for (q, re) in results:
                    request_data = {'summary': q.summary(),
                                    'command': q.command(),
                                    'object': export_object(q),
                                    'hash': q.hashret(),
                                    'display': q.display(),
                                    'sent_time': q.time}
                    response_data = {'summary': r.summary(),
                                     'command': r.command(),
                                     'object': export_object(r)
                                     'hash': r.hashret(),
                                     'src': r['IP'].src,
                                     'flags': r['IP'].flags,
                                     'display': r.display(),
                                     'recv_time': r.time,
                                     'delay': r.time - q.time}
                    if self.verbose:
                        request_data['hexdump'] = q.hexdump()
                        response_data['hexdump'] = r.hexdump()

                    result_data = (request_data, response_data)

                    flags = tcp_flags(response)
                    for dest, data in self.destinations.items():
                        if data['dst'] == response.src:
                            if not 'response' in data:
                                log.msg("%s" % request.summary())
                                log.msg("%s" % response.summary())
                                data['response'] = [response.summary()]
                                data['reachable'] = True
                            else:
                                data['response'].append(response.summary())
                    if self.verbose:
                        log.msg("%s" % request.summary())
                        log.msg("%s" % response.hexdump())

                for unans in unanswered:
                    process_unanswered(unans)

                #try:
                #    response.make_table(
                #        lambda x:(
                #            (x.src for x in received_syn(response)),
                #            (x.dport for x in request),
                #            (x for x in tcp.flags(response)) )
                #        )
                #except Exception, ex:
                #    log.exception(ex)

            def process_unanswered(unanswer):
                """Callback function to process unanswered packets."""
                log.msg("unanswered packets:\n%s"
                        % sort_nicely(unanswer))
                self.report['unanswered'] = sort_nicely(unanswer)

                for dest, data in self.destinations.items():
                    if not 'response' in data:
                        log.msg("No reply from %s." % dest)
                        data['response'] = None
                        data['reachable'] = False
                return unanswer

            (addr, port) = self.input
            packets = build_packets(addr, port)

            results = []

            d = txscapy.sr(packets, iface=self.interface)
            d.addCallbacks(process_packets, log.exception)
            self.report['destinations'] = self.destinations
            return d

        except Exception, e:
            log.exception(e)

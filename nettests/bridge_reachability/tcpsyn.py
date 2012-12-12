#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  +-----------+
#  | tcpflags.py |
#  +-----------+
#     Send packets with various TCP flags set to a test server 
#     to check that it is reachable.
#
# @authors: Isis Lovecruft, <isis@torproject.org>
# @version: 0.0.1-pre-alpha
# @license: copyright (c) 2012 Isis Lovecruft
#           see attached LICENCE file
#

import os
import sys

from twisted.python         import usage
from twisted.python.failure import Failure
from twisted.internet       import reactor, defer
from ooni                   import nettest, config
from ooni.utils             import net, log
from ooni.utils.otime       import timestamp

try:
    from scapy.all          import TCP, IP, sr
    from ooni.utils         import txscapy
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")


class TCPFlagsOptions(usage.Options):
    """Options for TCPTest."""
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['port', 'p', None, 'Host port'],
        ['flags', 's', 'S', 'Comma separated flags to set, eg. "SA"'],
        ['count', 'c', 3, 'Number of SYN packets to send', int],
        ['interface', 'i', None, 'Network interface to use'],
        ['hexdump', 'x', False, 'Show hexdump of responses']]

class TCPFlagsTest(nettest.NetTestCase):
    """
    Sends only a TCP SYN packet to a host IP:PORT, and waits for either a
    SYN/ACK, a RST, or an ICMP error.

    TCPSynTest can take an input file containing one IP:Port pair per line, or
    the commandline switches --dst <IP> and --port <PORT> can be used.
    """
    name         = 'TCP Flags'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A TCP SYN/ACK/FIN test to see if a host is reachable.'
    version      = '0.1.1'
    requiresRoot = True

    usageOptions = TCPFlagsOptions
    inputFile    = ['file', 'f', None, 'File of list of IP:PORTs to ping']

    destinations = {}

    def setUp(self, *a, **kw):
        """Configure commandline parameters for TCPSynTest."""
        if self.localOptions:
            for key, value in self.localOptions.items():
                setattr(self, key, value)
        if not self.interface:
            try:
                iface = net.getDefaultIface()
                self.interface = iface
            except net.IfaceError:
                self.abortClass("Could not find a working network interface!")
        if self.flags:
            self.flags = self.flags.split(',')
        if config.advanced.debug:
            defer.setDebugging('on')

    def addToDestinations(self, addr=None, port='443'):
        """
        Validate and add an IP address and port to the dictionary of
        destinations to send to. If the host's IP is already in the
        destinations, then only add the port.

        @param addr: A string representing an IPv4 or IPv6 address.
        @param port: A string representing a port number.
        @returns: A 2-tuple containing the address and port.
        """
        if addr is None:
            return (None, None) # do we want to return SkipTest?

        dst, dport = net.checkIPandPort(addr, port)
        if not dst in self.destinations.keys():
            self.destinations[dst] = {'dst': dst,
                                      'dport': [dport]}
        else:
            log.debug("Got additional port for destination.")
            self.destinations[dst]['dport'].append(dport)
        return (dst, dport)

    def inputProcessor(self, input_file=None):
        """
        Pull the IPs and PORTs from the commandline options first, and then
        from the input file, and place them in a dict for storing test results
        as they arrive.
        """
        if self.localOptions['dst'] is not None \
                and self.localOptions['port'] is not None:
            log.debug("Processing commandline destination")
            yield self.addToDestinations(self.localOptions['dst'],
                                         self.localOptions['port'])
        if input_file and os.path.isfile(input_file):
            log.debug("Processing input file %s" % input_file)
            with open(input_file) as f:
                for line in f.readlines():
                    if line.startswith('#'):
                        continue
                    one = line.strip()
                    raw_ip, raw_port = one.rsplit(':', 1)
                    yield self.addToDestinations(raw_ip, raw_port)

    def test_tcp_flags(self):
        """
        Generate, send, and listen for responses to, a list of TCP/IP packets
        to an address and port pair taken from the current input, and a string
        specifying the TCP flags to set.

        @param flags:
            A string representing the TCP flags to be set, i.e. "SA" or "F".
            Defaults to "S".
        """
        def build_packets(addr, port):
            """Construct a list of packets to send out."""
            packets = []
            for flag in self.flags:
                log.debug("Generating packets with %s flags for %s:%d..."
                          % (flag, addr, port))
                for x in xrange(self.count):
                    packets.append( IP(dst=addr)/TCP(dport=port, flags=flag) )
            return packets

        def process_packets(packet_list):
            """
            If the source address of packet in :param:packet_list matches one of
            our input destinations, then extract some of the information from it
            to the test report.

            @param packet_list:
                A :class:scapy.plist.PacketList
            """
            log.msg("Processing received packets...")
            results, unanswered = packet_list

            for (q, r) in results:
                request = {'dst': q.dst,
                           'dport': q.dport,
                           'summary': q.summary(),
                           'hexdump': None,
                           'sent_time': q.time}
                response = {'src': r['IP'].src,
                            'flags': r['IP'].flags,
                            'summary': r.summary(),
                            'hexdump': None,
                            'recv_time': r.time,
                            'delay': r.time - q.time}
                if self.hexdump:
                    request['hexdump'] = q.hexdump()
                    response['hexdump'] = r.hexdump()

                for dest, data in self.destinations.items():
                    if response['src'] == data['dst']:
                        log.msg(" Received response from %s:\n%s ==> %s" % (
                                response['src'], q.mysummary(), r.mysummary()))
                        if self.hexdump:
                            log.msg("%s\n%s" % (q.hexdump(), r.hexdump()))

                        self.report['request'] = request
                        self.report['response'] = response

            if unanswered is not None:
                unans = [un.summary() for un in unanswered]
                log.msg(" Waiting on responses from:\n%s" % '\n'.join(unans))
                self.report['unanswered'] = unans

        try:
            self.report = {}
            (addr, port) = self.input
            pkts = build_packets(addr, port)
            d = process_packets(sr(pkts, iface=self.interface, timeout=5))
            return d
        except Exception, ex:
            log.exception(ex)

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

from ipaddr                 import IPAddress
from twisted.python         import usage
from twisted.python.failure import Failure
from twisted.internet       import reactor, defer, address
from ooni                   import nettest, config
from ooni.utils             import net, log
from ooni.utils.otime       import timestamp

try:
    from scapy.all          import TCP, IP
    from ooni.utils         import txscapy
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")


class TCPFlagOptions(usage.Options):
    """Options for TCPTest."""
    optParameters = [
        ['dst', 'd', None, 'Host IP to ping'],
        ['port', 'p', None, 'Host port'],
        ['flags', 's', None, 'Comma separated flags to set [S|A|F]'],
        ['count', 'c', 3, 'Number of SYN packets to send', int],
        ['interface', 'i', None, 'Network interface to use'],
        ['hexdump', 'x', False, 'Show hexdump of responses'],
        ['pdf', 'y', False,
         'Create pdf of visual representation of packet conversations']]

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

    usageOptions = TCPFlagOptions
    inputFile    = ['file', 'f', None, 'File of list of IP:PORTs to ping']

    def setUp(self, *a, **kw):
        """Configure commandline parameters for TCPSynTest."""
        self.report = {}
        self.packets = {'results': [], 'unanswered': []}

        if self.localOptions:
            for key, value in self.localOptions.items():
                setattr(self, key, value)
        if not self.interface:
            try:
                iface = net.getDefaultIface()
            except net.IfaceError, ie:
                log.warn("Could not find a working network interface!")
                log.fail(ie)
            else:
                self.interface = iface
        if config.advanced.debug:
            defer.setDebugging('on')

    def addToDestinations(self, addr='0.0.0.0', port='443'):
        """
        Validate and add an IP address and port to the dictionary of
        destinations to send to. If the host's IP is already in the
        destinations, then only add the port.

        @param addr: A string representing an IPv4 or IPv6 address.
        @param port: A string representing a port number.
        @returns: A 2-tuple containing the address and port.
        """
        dst, dport = net.checkIPandPort(addr, port)
        if not dst in self.report.keys():
            self.report[dst] = {'dst': dst, 'dport': [dport]}
        else:
            log.debug("Got additional port for destination.")
            self.report[dst]['dport'].append(dport)
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

    def tcp_flags(self, flags=None):
        """
        Generate, send, and listen for responses to, a list of TCP/IP packets
        to an address and port pair taken from the current input, and a string
        specifying the TCP flags to set.

        @param flags:
            A string representing the TCP flags to be set, i.e. "SA" or "F".
            Defaults to "S".
        """
        def build_packets(addr, port, flags=None, count=3):
            """Construct a list of packets to send out."""
            packets = []
            for x in xrange(count):
                packets.append( IP(dst=addr)/TCP(dport=port, flags=flags) )
            return packets

        def process_packets(packet_list):
            """
            If the source address of packet in :param:packet_list matches one of
            our input destinations, then extract some of the information from it
            to the test report.

            @param packet_list:
                A :class:scapy.plist.PacketList
            """
            results, unanswered = packet_list
            self.packets['results'].append([r for r in results])
            self.packets['unanswered'].append([u for u in unanswered])
    
            for (q, r) in results:
                request_data = {'dst': q.dst,
                                'dport': q.dport,
                                'summary': q.summary(),
                                'command': q.command(),
                                'hexdump': None,
                                'sent_time': q.time}
                response_data = {'src': r['IP'].src,
                                 'flags': r['IP'].flags,
                                 'summary': r.summary(),
                                 'command': r.command(),
                                 'hexdump': None,
                                 'recv_time': r.time,
                                 'delay': r.time - q.time}
                if self.hexdump:
                    request_data.update('hexdump', q.hexdump())
                    response_data.update('hexdump', r.hexdump())

                for dest, data in self.report.items():
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
                            self.report[response_data['src']['data'].update(data)

            if unanswered is not None and len(unanswered) > 0:
                log.msg("Waiting on responses from\n%s" %
                        '\n'.join( [unans.summary() for unans in unanswered] ))
            log.msg("Writing response packet information to report...")
 
        (addr, port) = self.input
        packets = build_packets(addr, port, str(flags), self.count)
        d = txscapy.sr(packets, iface=self.interface)
        #d.addCallbacks(process_packets, log.exception)
        #d.addCallbacks(process_unanswered, log.exception)
        d.addCallback(process_packets)
        d.addErrback(process_unanswered)

        return d

    @log.catch
    def createPDF(self):
        pdfname = self.name + '_' + timestamp()
        self.packets['results'].pdfdump(pdfname)
        log.msg("Visual packet conversation saved to %s.pdf" % pdfname)

    def test_tcp_flags(self):
        """Send packets with given TCP flags to an address:port pair."""
        flag_list = self.flags.split(',')

        dl = []
        for flag in flag_list:
            dl.append(self.tcp_flags(flag))
        d = defer.DeferredList(dl)

        if self.pdf:
            d.addCallback(self.createPDF)

        return d

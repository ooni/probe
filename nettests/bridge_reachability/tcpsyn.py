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
        ['count', 'c', 3, 'Number of SYN packets to send', int],
        ['interface', 'i', None, 'Network interface to use'],
        ['hexdump', 'x', False, 'Show hexdump of responses'],
        ['pdf', 'y', False,
         'Create pdf of visual representation of packet conversations'],
        ['cerealize', 'z', False,
         'Cerealize scapy objects for further scripting']]

class TCPFlagTest(nettest.NetTestCase):
    """
    Sends only a TCP SYN packet to a host IP:PORT, and waits for either a
    SYN/ACK, a RST, or an ICMP error.

    TCPSynTest can take an input file containing one IP:Port pair per line, or
    the commandline switches --dst <IP> and --port <PORT> can be used.
    """
    name         = 'TCP Flag'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A TCP SYN/ACK/FIN test to see if a host is reachable.'
    version      = '0.0.1'
    requiresRoot = True

    usageOptions = TCPFlagOptions
    inputFile    = ['file', 'f', None, 'File of list of IP:PORTs to ping']

    #destinations = {}

    def setUp(self, *a, **kw):
        """Configure commandline parameters for TCPSynTest."""
        self.report = {}

        if self.localOptions:
            for key, value in self.localOptions.items():
                setattr(self, key, value)
        if not self.interface:
            try:
                iface = log.catch(net.getDefaultIface())
            except net.IfaceError, ie:
                log.warn("Could not find a working network interface!")
                log.fail(ie)
            else:
                log.msg("Using system default interface: %s" % iface)
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
        #if not dst in self.destinations.keys():
        if not dst in self.report.keys():
            #self.destinations[dst] = {'dst': dst, 'dport': [dport]}
            self.report[dst] = {'dst': dst, 'dport': [dport]}
        else:
            log.debug("Got additional port for destination.")
            #self.destinations[dst]['dport'].append(dport)
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

    @log.catch
    def createPDF(self, results):
        pdfname = self.name + '_' + timestamp()
        results.pdfdump(pdfname)
        log.msg("Visual packet conversation saved to %s.pdf" % pdfname)

    @staticmethod
    def build_packets(addr, port, flags=None, count=3):
        """Construct a list of packets to send out."""
        packets = []
        for x in xrange(count):
            packets.append( IP(dst=addr)/TCP(dport=port, flags=flags) )
        return packets

    @staticmethod
    def process_packets(packet_list):
        """
        If the source address of packet in :param:packet_list matches one of our input
        destinations, then extract some of the information from it to the test report.

        @param packet_list:
            A :class:scapy.plist.PacketList
        """
        results, unanswered = packet_list

        if self.pdf:
            self.createPDF(results)

        for (q, r) in results:
            request_data = {'dst': q.dst,
                            'dport': q.dport,
                            'summary': q.summary(),
                            'command': q.command(),
                            'sent_time': q.time}
            response_data = {'src': r['IP'].src,
                             'flags': r['IP'].flags,
                             'summary': r.summary(),
                             'command': r.command(),
                             'recv_time': r.time,
                             'delay': r.time - q.time}
            if self.hexdump:
                request_data.update('hexdump', q.hexdump())
                response_data.update('hexdump', r.hexdump())
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

    @staticmethod
    def process_unanswered(unanswered):
        """Callback function to process unanswered packets."""
        if unanswered is not None and len(unanswered) > 0:
            log.msg("Waiting on responses from\n%s" %
                    '\n'.join( [unans.summary() for unans in unanswered] ))
        log.msg("Writing response packet information to report...")
        self.report = (self.destinations)
        return self.destinations

    @log.catch
    def tcp_flags(self, flags="S"):
        """
        Generate, send, and listen for responses to, a list of TCP/IP packets
        to an address and port pair taken from the current input, and a string
        specifying the TCP flags to set.

        @param flags:
            A string representing the TCP flags to be set, i.e. "SA" or "F".
            Defaults to "S".
        """
        (addr, port) = self.input
        packets = self.build_packets(addr, port, str(flags), self.count)
        d = txscapy.sr(packets, iface=self.interface)
        d.addCallbacks(self.process_packets, log.exception)
        d.addCallbacks(self.process_unanswered, log.exception)
        return d

    def test_tcp_fin(self):
        """Send a list of FIN packets to an address and port pair from inputs."""
        return self.tcp_flags("F")

    def test_tcp_syn(self):
        """Send a list of SYN packets to an address and port pair from inputs."""
        return self.tcp_flags("S")

    def test_tcp_synack(self):
        """Send a list of SYN/ACK packets to an address and port pair from inputs."""
        return self.tcp_flags("SA")

    def test_tcp_ack(self):
        """Send a list of SYN packets to an address and port pair from inputs."""
        return self.tcp_flags("A")

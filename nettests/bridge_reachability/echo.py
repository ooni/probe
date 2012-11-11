#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  +---------+
#  | echo.py |
#  +---------+
#     A simple ICMP-8 ping test.
#
# :author: Isis Lovecruft
# :version: 0.0.1-pre-alpha
# :license: (c) 2012 Isis Lovecruft
#           see attached LICENCE file
#

import os
import sys

from pprint           import pprint

from twisted.internet import reactor
from twisted.plugin   import IPlugin
from twisted.python   import usage
from ooni.nettest     import NetTestCase
from ooni.utils       import log, Storage
from ooni.utils.net   import PermissionsError, IfaceError

try:
    from scapy.all             import sr1, IP, ICMP        ## XXX v4/v6?
    from ooni.lib              import txscapy
    from ooni.lib.txscapy      import txsr, txsend
    from ooni.templates.scapyt import BaseScapyTest
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")

class EchoTest(BaseScapyTest):
    """
    xxx fill me in
    """
    name         = 'echo'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A simple ICMP-8 test to see if a host is reachable.'
    version      = '0.0.1'
    inputFile    = ['file', 'f', None, 'File of list of IPs to ping']
    requiresRoot = True

    optParameters = [
        ['interface', 'i', None, 'Network interface to use'],
        ['count', 'c', 5, 'Number of packets to send', int],
        ['size', 's', 56, 'Number of bytes to send in ICMP data field', int],
        ['ttl', 'l', 25, 'Set the IP Time to Live', int],
        ['timeout', 't', 2, 'Seconds until timeout if no response', int],
        ['pcap', 'p', None, 'Save pcap to this file'],
        ['receive', 'r', True, 'Receive response packets']
        ]

    def setUp(self, *a, **kw):
        '''
        :ivar ifaces:
            Struct returned from getifaddrs(3) and turned into a tuple in the
            form (*ifa_name, AF_FAMILY, *ifa_addr)
        '''
        if self.localOptions:
            for key, value in self.localOptions.items():
                log.debug("setting self.%s = %s" % (key, value))
                setattr(self, key, value)

        self.timeout *= 1000            ## convert to milliseconds

        if not self.interface:
            log.msg("No network interface specified!")

        if self.pcap:
            try:
                self.pcapfile = open(self.pcap, 'a+')
            except:
                log.msg("Unable to write to pcap file %s" % self.pcap)
                self.pcapfile = None

        try:
            assert os.path.isfile(self.file)
            fp = open(self.file, 'r')
        except Exception, e:
            hosts = ['8.8.8.8', '38.229.72.14']
            log.err(e)
        else:
            self.inputs = self.inputProcessor(fp)
        self.removePorts(hosts)

        log.debug("Initialization of %s test completed with:\n%s"
                  % (self.name, ''.join(self.__dict__)))

    @staticmethod
    def inputParser(self, one_input):
        log.debug("Removing possible ports from host addresses...")
        log.debug("Initial inputs:\n%s" % pprint(inputs))

        #host = [h.rsplit(':', 1)[0] for h in inputs]
        host = h.rsplit(':', 1)[0]
        log.debug("Inputs converted to:\n%s" % hosts)

        return host

    def tryInterfaces(self, ifaces):
        try:
            from scapy.all import sr1   ## we want this check to be blocking
        except:
            log.msg("This test requires scapy: www.secdev.org/projects/scapy")
            raise SystemExit

        ifup = {}
        while ifaces:
            for ifname, ifaddr in ifaces:
                log.debug("Currently testing network capabilities of interface"
                          + "%s  by sending a packet to our address %s"
                          % (ifname, ifaddr))
                try:
                    pkt = IP(dst=ifaddr)/ICMP()
                    ans, unans = sr(pkt, iface=ifname, timeout=self.timeout)
                except Exception, e:
                    raise PermissionsError if e.find("Errno 1") else log.err(e)
                else:
                    ## xxx i think this logic might be wrong
                    log.debug("Interface test packet\n%s\n\n%s"
                              % (pkt.summary(), pkt.show2()))
                    if ans.summary():
                        log.info("Received answer for test packet on interface"
                                 +"%s :\n%s" % (ifname, ans.summary()))
                        ifup.update(ifname, ifaddr)
                    else:
                        log.info("Our interface test packet was unanswered:\n%s"
                                 % unans.summary())

        if len(ifup) > 0:
            log.msg("Discovered the following working network interfaces: %s"
                    % ifup)
            return ifup
        else:
            raise IfaceError("Could not find a working network interface.")

    def test_icmp(self):
        self.sr(IP(dst=self.input)/ICMP())


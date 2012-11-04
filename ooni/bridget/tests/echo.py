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
    from ooni.templates.scapyt import ScapyTest
except:
    log.msg("This test requires scapy, see www.secdev.org/projects/scapy")

## xxx TODO: move these to a utility function for determining OSes
LINUX=sys.platform.startswith("linux")
OPENBSD=sys.platform.startswith("openbsd")
FREEBSD=sys.platform.startswith("freebsd")
NETBSD=sys.platform.startswith("netbsd")
DARWIN=sys.platform.startswith("darwin")
SOLARIS=sys.platform.startswith("sunos")
WINDOWS=sys.platform.startswith("win32")

class EchoTest(ScapyTest):
    """
    xxx fill me in
    """
    name         = 'echo'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A simple ICMP-8 test to see if a host is reachable.'
    version      = '0.0.1'
    inputFile    = ['file', 'f', None, 'File of list of IPs to ping']
    requirements = None
    report       = Storage()

    optParameters = [
        ['interface', 'i', None, 'Network interface to use'],
        ['count', 'c', 5, 'Number of packets to send', int],
        ['size', 's', 56, 'Number of bytes to send in ICMP data field', int],
        ['ttl', 'l', 25, 'Set the IP Time to Live', int],
        ['timeout', 't', 2, 'Seconds until timeout if no response', int],
        ['pcap', 'p', None, 'Save pcap to this file'],
        ['receive', 'r', True, 'Receive response packets']
        ]

    def setUpClass(self, *a, **kw):
        '''
        :ivar ifaces:
            Struct returned from getifaddrs(3) and turned into a tuple in the
            form (*ifa_name, AF_FAMILY, *ifa_addr)
        '''
        super(EchoTest, self).__init__(*a, **kw)

        ## allow subclasses which register/implement external classes
        ## to define their own reactor without overrides:
        if not hasattr(super(EchoTest, self), 'reactor'):
            log.debug("%s test: Didn't find reactor!" % self.name)
            self.reactor = reactor

        if self.localOptions:
            log.debug("%s localOptions found" % self.name)
            log.debug("%s test options: %s" % (self.name, self.subOptions))
            self.local_options = self.localOptions.parseOptions(self.subOptions)
            for key, value in self.local_options:
                log.debug("Set attribute %s[%s] = %s" % (self.name, key, value))
                setattr(self, key, value)

        ## xxx is this now .subOptions?
        #self.inputFile = self.localOptions['file']
        self.timeout *= 1000            ## convert to milliseconds

        if not self.interface:
            log.msg("No network interface specified!")
            log.debug("OS detected: %s" % sys.platform)
            if LINUX or OPENBSD or NETBSD or FREEBSD or DARWIN or SOLARIS:
                from twisted.internet.test import _posixifaces
                log.msg("Attempting to discover network interfaces...")
                ifaces = _posixifaces._interfaces()
            elif WINDOWS:
                from twisted.internet.test import _win32ifaces
                log.msg("Attempting to discover network interfaces...")
                ifaces = _win32ifaces._interfaces()
            else:
                log.debug("Client OS %s not accounted for!" % sys.platform)
                log.debug("Unable to discover network interfaces...")
                ifaces = [('lo', '')]

            ## found = {'eth0': '1.1.1.1'}
            found = [{i[0]: i[2]} for i in ifaces if i[0] != 'lo']
            log.info("Found interfaces:\n%s" % pprint(found))
            self.interfaces = self.tryInterfaces(found)
        else:
            ## xxx need a way to check that iface exists, is up, and
            ## we have permissions on it
            log.debug("Our interface has been set to %s" % self.interface)

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
    def inputParser(inputs):
        log.debug("Removing possible ports from host addresses...")
        log.debug("Initial inputs:\n%s" % pprint(inputs))

        assert isinstance(inputs, list)
        hosts = [h.rsplit(':', 1)[0] for h in inputs]
        log.debug("Inputs converted to:\n%s" % hosts)

        return hosts

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

    def buildPackets(self):
        log.debug("self.input is %s" % self.input)
        log.debug("self.hosts is %s" % self.hosts)
        for addr in self.input:
            packet = IP(dst=self.input)/ICMP()
            self.request.append(packet)
        return packet

    def test_icmp(self):
        if self.recieve:
            self.buildPackets()
            all = []
            for packet in self.request:
                d = self.sendReceivePackets(packets=packet)
                all.append(d)
                self.response.update({packet: d})
            d_list = defer.DeferredList(all)
            return d_list
        else:
            d = self.sendPackets()
            return d

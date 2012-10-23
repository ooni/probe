#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
#  +---------+
#  | echo.py |
#  +---------+
#     A simply ICMP-8 ping test.
#
# :author: Isis Lovecruft
# :version: 0.0.1-pre-alpha
# :license: (c) 2012 Isis Lovecruft
#           see attached LICENCE file
#

import os
import sys

from twisted.plugin import IPlugin
from twisted.python import usage
from zope.interface import implements

from ooni.lib                  import txscapy
from ooni.utils                import log
from ooni.plugoo.assets        import Asset
from ooni.plugoo.interface     import ITest
from ooni.protocols.scapyproto import ScapyTest

from ooni import nettest

class EchoOptions(nettest.):
    optParameters = [
        ['interface', 'i', None, 'Network interface to use'],
        ['destination', 'd', None, 'File of hosts to ping'],
        ['count', 'c', 5, 'Number of packets to send', int],
        ['size', 's', 56, 'Number of bytes to send in ICMP data field', int],
        ['ttl', 't', 25, 'Set the IP Time to Live', int],
        ]
    optFlags = []

class EchoAsset(Asset):
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

    def parse_line(self, line):
        if line.startswith('#'):
            return
        else:
            return line.replace('\n', '')

class EchoTest(ScapyTest):
    implements(IPlugin, ITest)

    shortName    = 'echo'
    description  = 'A simple ICMP-8 test to check if a host is reachable'
    options      = EchoOptions
    requirements = None
    blocking     = False

    pcap_file = 'echo.pcap'
    receive   = True

    def initialize(self):
        self.request = {}
        self.response = {}

        if self.local_options:

            options = self.local_options

            if options['interface']:
                self.interface = options['interface']

            if options['count']:
                ## there's a Counter() somewhere, use it
                self.count = options['count']

            if options['size']:
                self.size = options['size']

            if options['ttl']:
                self.ttl = options['ttl']

    def load_assets(self):
        assets = {}
        option = self.local_options

        if option and option['destination']:

            try:
                from scapy.all import IP
            except:
                log.err()

            if os.path.isfile(option['destination']):
                with open(option['destination']) as hosts:
                    for line in hosts.readlines():
                        assets.update({'host': EchoAsset(line)})
            else:
                while type(options['destination']) is str:
                    try:
                        IP(options['destination'])
                    except:
                        log.err()
                        break
                    assets.update({'host': options['destination']})
                else:
                    log.msg("Couldn't understand destination option...")
                    log.msg("Give one IPv4 address, or a file with one address per line.")
        return assets

    def experiment(self, args):
        if len(args) == 0:
            log.err("Error: We're Echo, not Narcissus!")
            log.err("       Provide a list of hosts to ping...")
            d = sys.exit(1)
            return d

        ## XXX v4 / v6
        from scapy.all import ICMP, IP, sr
        ping = sr(IP(dst=args)/ICMP())
        if ping:
            self.response.update(ping.show())
        else:
            log.msg('No response received from %s' % args)

    def control(self, *args):
        pass

echo = EchoTest(None, None, None)

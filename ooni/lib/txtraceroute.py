#!/usr/bin/env python
# coding: utf-8
#
# Copyright (c) 2012 Alexandre Fiori
#                    Arturo Filastò
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import json
import operator
import os
import socket
import struct
import sys
import time
import random
import itertools
from pprint import pprint

from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import threads
from twisted.python import usage
from twisted.web.client import getPage

class iphdr(object):
    """
    This represents an IP packet header.

    XXX enable IP_TIMESTAMP in setsockopt
        to get the timestamp of when the router says it has gotten an ICMP
        timeout.

    @assemble packages the packet
    @disassemble disassembles the packet
    """
    def __init__(self, proto=socket.IPPROTO_ICMP, src="0.0.0.0", dst=None):
        self.version = 4
        self.hlen = 5
        self.tos = 0
        self.length = 20
        self.id = os.getpid()
        self.frag = 0
        self.ttl = 255
        self.proto = proto
        self.cksum = 0
        self.src = src
        self.saddr = socket.inet_aton(src)
        self.dst = dst or "0.0.0.0"
        self.daddr = socket.inet_aton(self.dst)
        self.data = ""

    def assemble(self):
        header = struct.pack('BBHHHBB',
                             (self.version & 0x0f) << 4 | (self.hlen & 0x0f),
                             self.tos, self.length + len(self.data),
                             socket.htons(self.id), self.frag,
                             self.ttl, self.proto)
        self._raw = header + "\x00\x00" + self.saddr + self.daddr + self.data
        return self._raw

    @classmethod
    def disassemble(self, data):
        self._raw = data
        ip = iphdr()
        pkt = struct.unpack('!BBHHHBBH', data[:12])
        ip.version = (pkt[0] >> 4 & 0x0f)
        ip.hlen = (pkt[0] & 0x0f)
        ip.tos, ip.length, ip.id, ip.frag, ip.ttl, ip.proto, ip.cksum = pkt[1:]
        ip.saddr = data[12:16]
        ip.daddr = data[16:20]
        ip.src = socket.inet_ntoa(ip.saddr)
        ip.dst = socket.inet_ntoa(ip.daddr)
        return ip

    def __repr__(self):
        return "IP (tos %s, ttl %s, id %s, frag %s, proto %s, length %s) " \
               "%s -> %s" % \
               (self.tos, self.ttl, self.id, self.frag, self.proto,
                self.length, self.src, self.dst)

class tcphdr(object):
    def __init__(self, data="", sport=4242, dport=4242):
        self.seq = 0
        self.hlen = 44
        self.flags = 2
        self.wsize = 200
        self.cksum = 123
        self.options = 0
        self.mss = 1460
        self.dport = dport
        self.sport = sport

    def assemble(self):
        header = struct.pack("!HHL", self.sport, self.dport, self.seq)
        header += '\x00\x00\x00\x00'
        header += struct.pack("!HHH", (self.hlen & 0xff) << 10 | (self.flags &
            0xff), self.wsize, self.cksum)
        header += "\x00\x00"
        options = '\x02\x04\x05\xb4\x01\x03\x03\x01\x01\x01\x08\x0a'
        options += '\x4d\xcf\x52\x33\x00\x00\x00\x00\x04\x02\x00\x00'
        # XXX There is something wrong here fixme
        # options = struct.pack("!LBBBBBB", self.mss, 1, 3, 3, 1, 1, 1)
        # options += struct.pack("!BBL", 8, 10, 1209452188)
        # options += '\00'*4
        # options += struct.pack("!BB", 4, 2)
        # options += '\00'
        self._raw = header+options
        return self._raw

    @classmethod
    def checksum(self, data):
        pass

    def __repr__(self):
        return "<TCPPacket (sport: %s dport: %s seq: %s) " %\
               (self.sport, self.dport, self.seq)

    @classmethod
    def disassemble(self, data):
        self._raw = data
        tcp = tcphdr()
        pkt = struct.unpack("!HHL", data[:8])
        tcp.sport, tcp.dport, tcp.seq = pkt
        if len(data) > 10:
            pkt = struct.unpack("!H", data[8:10])
            tcp.hlen = (pkt[0] >> 10 ) & 0xff
            tcp.flags = pkt[0] & 0xff
            tcp.wsize, tcp.cksum = struct.unpack("!HH", data[20:24])
        return tcp

class udphdr(object):
    def __init__(self, data="", sport=4242, dport=4242):
        self.dport = dport
        self.sport = sport
        self.cksum = 0
        self.length = 0
        self.data = data

    def assemble(self):
        self.length = len(self.data) + 8
        part1 = struct.pack("!HHH", self.sport, self.dport, self.length)
        cksum = self.checksum(self.data)
        cksum = struct.pack("!H", cksum)

        self._raw = part1 + cksum + self.data
        return self._raw

    @classmethod
    def checksum(self, data):
        # XXX implement proper checksum
        cksum = 0
        return cksum

    def __repr__(self):
        return "<UDPPacket (sport %s, dport %s, length %s, data %s)>" % \
               (self.sport, self.dport, self.length, self.data)

    @classmethod
    def disassemble(self, data):
        self._raw = data
        udp = udphdr()
        pkt = struct.unpack("!HHHH", data[:8])
        udp.sport, udp.dport, udp.length, udp.cksum = pkt
        udp.data = data[8:]
        return udp

class icmphdr(object):
    def __init__(self, data=""):
        self.type = 8
        self.code = 0
        self.cksum = 0
        self.id = os.getpid()
        self.sequence = 0
        self.data = data

    def assemble(self):
        part1 = struct.pack("BB", self.type, self.code)
        part2 = struct.pack("!HH", self.id, self.sequence)
        cksum = self.checksum(part1 + "\x00\x00" + part2 + self.data)
        cksum = struct.pack("!H", cksum)
        self._raw = part1 + cksum + part2 + self.data
        return self._raw

    @classmethod
    def checksum(self, data):
        if len(data) & 1:
            data += "\x00"
        cksum = reduce(operator.add,
                       struct.unpack('!%dH' % (len(data) >> 1), data))
        cksum = (cksum >> 16) + (cksum & 0xffff)
        cksum += (cksum >> 16)
        cksum = (cksum & 0xffff) ^ 0xffff
        return cksum

    @classmethod
    def disassemble(self, data):
        self._raw = data
        icmp = icmphdr()
        pkt = struct.unpack("!BBHHH", data)
        icmp.type, icmp.code, icmp.cksum, icmp.id, icmp.sequence = pkt
        return icmp

    def __repr__(self):
        return "ICMP (type %s, code %s, id %s, sequence %s)" % \
               (self.type, self.code, self.id, self.sequence)


def pprintp(packet):
    """
    Used to pretty print packets.
    """
    lines = []
    line = []
    for i, byte in enumerate(packet):
        line.append(("%.2x" % ord(byte), byte))
        if (i + 1) % 8 == 0:
            lines.append(line)
            line = []

    lines.append(line)

    for row in lines:
        left = ""
        right = "   " * (8 - len(row))
        for y in row:
            left += "%s " % y[0]
            right += "%s" % y[1]

        print left + "     " + right

@defer.inlineCallbacks
def geoip_lookup(ip):
    try:
        r = yield getPage("http://freegeoip.net/json/%s" % ip)
        d = json.loads(r)
        items = [d["country_name"], d["region_name"], d["city"]]
        text = ", ".join([s for s in items if s])
        defer.returnValue(text.encode("utf-8"))
    except Exception:
        defer.returnValue("Unknown location")


@defer.inlineCallbacks
def reverse_lookup(ip):
    try:
        r = yield threads.deferToThread(socket.gethostbyaddr, ip)
        defer.returnValue(r[0])
    except Exception:
        defer.returnValue(None)


class Hop(object):
    def __init__(self, target, ttl, proto, sport=None, dport=None):
        self.proto = proto
        self.dport = dport
        self.sport = sport

        self.found = False
        self.tries = 0
        self.last_try = 0
        self.remote_ip = None
        self.remote_icmp = None
        self.remote_host = None
        self.location = ""

        self.ttl = ttl
        self.ip = iphdr(dst=target)
        self.ip.ttl = ttl
        self.ip.id += ttl
        if self.proto == "icmp":
            self.icmp = icmphdr('\x00'*20)
            self.icmp.id = self.ip.id
            self.ip.data = self.icmp.assemble()
        elif self.proto == "udp":
            self.udp = udphdr('\x00'*20, self.sport, self.dport)
            self.ip.data = self.udp.assemble()
            self.ip.proto = socket.IPPROTO_UDP
        else:
            self.tcp = tcphdr('\x42'*20, self.sport, self.dport)
            self.ip.data = self.tcp.assemble()
            self.ip.proto = socket.IPPROTO_TCP

        self._pkt = self.ip.assemble()

    @property
    def pkt(self):
        self.tries += 1
        self.last_try = time.time()
        return self._pkt

    def get(self):
        if self.found:
            if self.remote_host:
                ip = self.remote_host
            else:
                ip = self.remote_ip.src
            ping = self.found - self.last_try
        else:
            ip = None
            ping = None

        location = self.location if self.location else None
        return {'ttl': self.ttl, 'ping': ping, 'ip': ip, 'location': location,
                'proto': self.proto, 'dport': self.dport, 'sport': self.sport}

    def __repr__(self):
        if self.found:
            if self.remote_host:
                ip = ":: %s" % self.remote_host
            else:
                ip = ":: %s" % self.remote_ip.src
            ping = "%0.3fs" % (self.found - self.last_try)
        else:
            ip = "??"
            ping = "-"

        location = ":: %s" % self.location if self.location else ""
        return "%02d. %s %s %s (%s, sport: %s dport: %s)" % (self.ttl, ping, ip, location, self.proto, self.sport, self.dport)

class TracerouteResult(object):
    """
    Used to store the results of a Traceroute.
    """
    #src_ports = [0, 9090]
    #dst_ports = [0, 21, 123, 80, 443]
    src_ports = [0, 80]
    dst_ports = [0, 80]
    hops = []
    done = False

    def __init__(self, protocol):
        self.protocol = protocol
        self.probes = {}

        if protocol == "icmp":
            self.current = None
        else:
            self.current = {}
            for src, dst in itertools.product(self.src_ports,
                                              self.dst_ports):
                if src not in self.probes:
                    self.probes[src] = {}
                self.probes[src][dst] = []

                if src not in self.current:
                    self.current[src] = {}
                self.current[src][dst] = None

    def get_current_probes(self):
        if self.protocol == "icmp":
            return self.current

    def add_to_current_probes(self, probe):
        if self.protocol == "icmp":
            self.current = probe
        else:
            self.current[probe.sport][probe.dport] = probe

    def is_in_progress(self):
        if self.protocol == "icmp":
            progress = self.current
        else:
            progress = None
            for x in self.current:
                for y in self.current[x]:
                    if self.current[x][y] != None:
                        progress = True
        if progress is None:
            return False
        else:
            return True

    def get(self, src=None, dst=None):
        if self.protocol == "icmp":
            return self.probes
        else:
            return self.probes[src][dst]

    def append(self, probe, src=None, dst=None):
        if self.protocol == "icmp":
            self.probes.append(hop)
        else:
            self.probes[src][dst].append(probe)

    def pop(self, src=None, dst=None):
        if self.protocol == "icmp":
            hop = self.current
            self.current = None
            return hop

        elif (dst != None) and (src != None):
            hop = self.current[src][dst]
            self.current[src][dst] = None
            return hop

        else:
            raise Exception("Did not specify dst and src ports")

    @classmethod
    def hops(self, target, ttl):
        """
        Generates a set of ooni probes for traceroute based network tampering
        detection.

        We send in one round a set of packets with same TTL but on all protocols
        and with all possible source and destination ports.
        """
        hops = []
        for src, dst in itertools.product(self.src_ports, self.dst_ports):
            hops.append(Hop(target, ttl,
                            "tcp", src, dst))
            hops.append(Hop(target, ttl,
                            "udp", src, dst))
        hops.append(Hop(target, ttl, "icmp", 0, 0))
        return hops

class TracerouteProtocol(object):
    def __init__(self, target, **settings):

        self.target = target
        self.settings = settings
        self.verbose = settings.get("verbose")
        self.proto = settings.get("proto")
        self.rfd = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                 socket.IPPROTO_ICMP)
        self.sfd = {}

        # Create the data structures to contain the test results
        self.traceroute = {}
        self.traceroute["tcp"] = TracerouteResult("tcp")
        self.traceroute["udp"] = TracerouteResult("udp")
        self.traceroute["icmp"] = TracerouteResult("icmp")

        if self.settings.get("ooni"):
            self.sfd["tcp"] = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                    socket.IPPROTO_TCP)
            self.sfd["icmp"] = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                    socket.IPPROTO_ICMP)
            self.sfd["udp"] = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                    socket.IPPROTO_UDP)
        elif self.proto == "icmp":
            self.sfd["icmp"] = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                    socket.IPPROTO_ICMP)
        elif self.proto == "udp":
            self.sfd["udp"] = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                    socket.IPPROTO_UDP)
        elif self.proto == "tcp":
            self.sfd["tcp"] = socket.socket(socket.AF_INET, socket.SOCK_RAW,
                                    socket.IPPROTO_TCP)

        # Let me add IP Headers myself, just give me a socket!
        self.rfd.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        for fd in self.sfd:
            self.sfd[fd].setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        self.out_queue = []
        self.waiting = True
        self.deferred = defer.Deferred()

        reactor.addReader(self)
        reactor.addWriter(self)

        # send 1st probe packet(s)
        if self.settings.get("ooni"):
            hops = list(TracerouteResult.hops(self.target, 1))
        else:
            hops = [Hop(self.target, 1,
                        settings.get("proto"),
                        self.settings.get("sport"),
                        self.settings.get("dport"))]
        for hop in hops:
            # Store the to be completed items inside of a dictionary
            self.traceroute[hop.proto].add_to_current_probes(hop)
            self.out_queue.append(hop)

    def logPrefix(self):
        return "TracerouteProtocol(%s)" % self.target

    def fileno(self):
        return self.rfd.fileno()

    @defer.inlineCallbacks
    def hopFound(self, hop, ip, icmp, ref, subref):
        hop.remote_ip = ip
        hop.remote_icmp = icmp

        if (ip and icmp):
            hop.found = time.time()
            if self.settings.get("geoip_lookup") is True:
                hop.location = yield geoip_lookup(ip.src)

            if self.settings.get("reverse_lookup") is True:
                hop.remote_host = yield reverse_lookup(ip.src)

        ttl = hop.ttl + 1

        if (ttl > (self.settings.get("max_hops", 30) + 1)):
            done = True
        else:
            done = False

        if not done:
            cb = self.settings.get("hop_callback")
            if callable(cb):
                yield defer.maybeDeferred(cb, hop)

        if not self.waiting:
            if self.deferred:
                self.deferred.callback(self.hops)
                self.deferred = None
        else:
            hops = []
            if self.settings.get("ooni"):
                if not (self.traceroute["icmp"].is_in_progress() or
                        self.traceroute["tcp"].is_in_progress() or
                        self.traceroute["udp"].is_in_progress()):
                    # Add hops only if we are not in progress
                    hops = list(TracerouteResult.hops(self.target, ttl))
            else:
                hops = [Hop(self.target, ttl,
                            settings.get("proto"),
                            self.settings.get("sport"),
                            self.settings.get("dport"))]

            for hop in hops:
                # Store the to be completed items inside of a dictionary
                self.traceroute[hop.proto].add_to_current_probes(hop)
                self.out_queue.append(hop)

    def doRead(self):
        if not self.waiting:
            return

        pkt = self.rfd.recv(4096)
        # disassemble ip header
        ip = iphdr.disassemble(pkt[:20])

        if self.verbose:
            print "Got this packet:"
            print "src %s" % ip.src
            pprintp(pkt)

        # Not interested in non ICMP packets.
        if ip.proto != socket.IPPROTO_ICMP:
            return

        found = False
        foundHop = None

        # disassemble icmp header
        icmp = icmphdr.disassemble(pkt[20:28])

        if self.verbose:
            print icmp

        # If it's an ICMP Echo reply then our ICMP probe has hit destination
        if icmp.type == 0 and icmp.id == self.current_hop["icmp"][1].icmp.id:
            foundHop = self.traceroute["icmp"].pop()
            found = True

        elif icmp.type == 11:
            # disassemble referenced ip header
            ref = iphdr.disassemble(pkt[28:48])
            subref = None

            if self.verbose:
                print ref

            if ref.dst == self.target:
                found = True

            if ref.proto == socket.IPPROTO_UDP:
                subref = udphdr.disassemble(pkt[48:])
                proto = "udp"

            elif ref.proto == socket.IPPROTO_TCP:
                subref = tcphdr.disassemble(pkt[48:])
                proto = "tcp"

            else:
                proto = "icmp"

            if subref:
                sport = subref.sport
                dport = subref.dport
            else:
                sport = None
                dport = None
            # Remove completed hops
            foundHop = self.traceroute[proto].pop(sport,
                                                  dport)

        if ip.src == self.target:
            self.waiting = False

        if found:
            self.hopFound(foundHop, ip, icmp, ref, subref)
        elif foundHop:
            self.hopFound(foundHop, ip, icmp, ref, subref)

    def hopTimeout(self, hop):
        if not hop.found:
            if hop.tries < self.settings.get("max_tries", 3):
                # retry
                hop.tries += 1
                self.out_queue.append(hop)
            else:
                # give up and move forward
                self.traceroute[hop.proto].pop(hop.dport,
                                               hop.sport)
                self.hopFound(hop, None, None, None, None)

    def doWrite(self):
        if self.waiting and self.out_queue:
            hop = self.out_queue.pop(0)
            pkt = hop.pkt
            if self.verbose:
                print "Sending this packet:"
                pprintp(pkt)
                print hop

            self.sfd[hop.proto].sendto(pkt, (hop.ip.dst, 0))

            self.traceroute[hop.proto].add_to_current_probes(hop)

            timeout = self.settings.get("timeout", 1)
            reactor.callLater(timeout, self.hopTimeout, hop)

    def connectionLost(self, why):
        pass


def traceroute(target, **settings):
    tr = TracerouteProtocol(target, **settings)
    return tr.deferred


@defer.inlineCallbacks
def start_trace(target, **settings):
    hops = yield traceroute(target, **settings)
    if settings["hop_callback"] is None:
        for hop in hops:
            print hop
    reactor.stop()

class Options(usage.Options):
    optFlags = [
        ["quiet", "q", "Only print results at the end."],
        ["no-dns", "n", "Show numeric IPs only, not their host names."],
        ["no-geoip", "g", "Do not collect and show GeoIP information"],
        ["verbose", "v", "Be more verbose"],
        ["ooni", "o", "Run the ooni common port multiprotocol traceroute"],
        ["help", "h", "Show this help"],
    ]
    optParameters = [
        ["timeout", "t", 2, "Timeout for probe packets"],
        ["tries", "r", 3, "How many tries before give up probing a hop"],
        ["proto", "p", "icmp", "What protocol to use (tcp, udp, icmp)"],
        ["dport", "d", random.randint(2**10, 2**16), "Destination port (TCP and UDP only)"],
        ["sport", "s", random.randint(2**10, 2**16), "Source port (TCP and UDP only)"],
        ["max_hops", "m", 30, "Max number of hops to probe"]
    ]

def main():
    def show(hop):
        print hop

    defaults = dict(hop_callback=show,
                    reverse_lookup=True,
                    geoip_lookup=True,
                    timeout=2,
                    proto="icmp",
                    dport=None,
                    sport=None,
                    verbose=False,
                    ooni=False,
                    max_tries=3,
                    max_hops=30)

    if len(sys.argv) < 2:
        print("Usage: %s [options] host" % (sys.argv[0]))
        print("%s: Try --help for usage details." % (sys.argv[0]))
        sys.exit(1)

    target = sys.argv.pop(-1) if sys.argv[-1][0] != "-" else ""
    config = Options()
    try:
        config.parseOptions()
        if not target:
            raise
    except usage.UsageError, e:
        print("%s: %s" % (sys.argv[0], e))
        print("%s: Try --help for usage details." % (sys.argv[0]))
        sys.exit(1)

    settings = defaults.copy()
    if config.get("silent"):
        settings["hop_callback"] = None
    if config.get("no-dns"):
        settings["reverse_lookup"] = False
    if config.get("no-geoip"):
        settings["geoip_lookup"] = False
    if config.get("verbose"):
        settings["verbose"] = True
    if config.get("ooni"):
        settings["ooni"] = True
    if "timeout" in config:
        settings["timeout"] = config["timeout"]
    if "tries" in config:
        settings["max_tries"] = config["tries"]
    if "proto" in config:
        settings["proto"] = config["proto"]
    if "max_hops" in config:
        settings["max_hops"] = config["max_hops"]
    if "dport" in config:
        settings["dport"] = int(config["dport"])
    if "sport" in config:
        settings["sport"] = int(config["sport"])

    if os.getuid() != 0:
        print("traceroute needs root privileges for the raw socket")
        sys.exit(1)
    try:
        target = socket.gethostbyname(target)
    except Exception, e:
        print("could not resolve '%s': %s" % (target, str(e)))
        sys.exit(1)

    reactor.callWhenRunning(start_trace, target, **settings)
    reactor.run()

if __name__ == "__main__":
    main()


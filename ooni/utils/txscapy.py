import struct
import socket
import os
import sys
import time
import random

from twisted.internet import protocol, base, fdesc
from twisted.internet import reactor, threads, error
from twisted.internet import defer, abstract
from zope.interface import implements

from scapy.config import conf
from scapy.supersocket import L3RawSocket
from scapy.all import RandShort, IP, IPerror, ICMP, ICMPerror
from scapy.all import TCP, TCPerror, UDP, UDPerror

from ooni.utils import log
from ooni.settings import config

class LibraryNotInstalledError(Exception):
    pass

def pcapdnet_installed():
    """
    Checks to see if libdnet or libpcap are installed and set the according
    variables.

    Returns:

        True
            if pypcap and libdnet are installed

        False
            if one of the two is absent
    """
    # In debian libdnet is called dumbnet instead of dnet, but scapy is
    # expecting "dnet" so we try and import it under such name.
    try:
        import dumbnet
        sys.modules['dnet'] = dumbnet
    except ImportError: pass

    try:
        conf.use_pcap = True
        conf.use_dnet = True
        from scapy.arch import pcapdnet

        config.pcap_dnet = True

    except ImportError:
        log.err("pypcap or dnet not installed. "
                "Certain tests may not work.")

        config.pcap_dnet = False
        conf.use_pcap = False
        conf.use_dnet = False

    # This is required for unix systems that are different than linux (OSX for
    # example) since scapy explicitly wants pcap and libdnet installed for it
    # to work.
    try:
        from scapy.arch import pcapdnet
    except ImportError:
        log.err("Your platform requires to having libdnet and libpcap installed.")
        raise LibraryNotInstalledError

    return config.pcap_dnet

if pcapdnet_installed():
    from scapy.all import PcapWriter

else:
    class DummyPcapWriter:
        def __init__(self, pcap_filename, *arg, **kw):
            log.err("Initializing DummyPcapWriter. We will not actually write to a pcapfile")

        @staticmethod
        def write(self):
            pass

    PcapWriter = DummyPcapWriter

from scapy.all import Gen, SetGen, MTU

def getNetworksFromRoutes():
    """ Return a list of networks from the routing table """
    from scapy.all import conf, ltoa, read_routes
    from ipaddr    import IPNetwork, IPAddress

    ## Hide the 'no routes' warnings
    conf.verb = 0

    networks = []
    for nw, nm, gw, iface, addr in read_routes():
        n = IPNetwork( ltoa(nw) )
        (n.netmask, n.gateway, n.ipaddr) = [IPAddress(x) for x in [nm, gw, addr]]
        n.iface = iface
        if not n.compressed in networks:
            networks.append(n)

    return networks

class IfaceError(Exception):
    pass

def getDefaultIface():
    """ Return the default interface or raise IfaceError """
    #XXX: currently broken on OpenVZ environments, because
    # the routing table does not contain a default route
    # Workaround: Set the default interface in ooniprobe.conf
    networks = getNetworksFromRoutes()
    for net in networks:
        if net.is_private:
            return net.iface
    raise IfaceError

def hasRawSocketPermission():
    try:
        socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_RAW)
        return True
    except socket.error:
        return False

class ProtocolNotRegistered(Exception):
    pass

class ProtocolAlreadyRegistered(Exception):
    pass

class ScapyFactory(abstract.FileDescriptor):
    """
    Inspired by muxTCP scapyLink:
    https://github.com/enki/muXTCP/blob/master/scapyLink.py
    """
    def __init__(self, interface, super_socket=None, timeout=5):

        abstract.FileDescriptor.__init__(self, reactor)
        if interface == 'auto':
            interface = getDefaultIface()
        if not super_socket and sys.platform == 'darwin':
            super_socket = conf.L3socket(iface=interface, promisc=True, filter='')
        elif not super_socket:
            super_socket = L3RawSocket(iface=interface, promisc=True)

        self.protocols = []
        fdesc._setCloseOnExec(super_socket.ins.fileno())
        self.super_socket = super_socket

    def writeSomeData(self, data):
        """
        XXX we actually want to use this, but this requires overriding doWrite
        or writeSequence.
        """
        pass

    def send(self, packet):
        """
        Write a scapy packet to the wire.
        """
        return self.super_socket.send(packet)

    def fileno(self):
        return self.super_socket.ins.fileno()

    def doRead(self):
        packet = self.super_socket.recv(MTU)
        if packet:
            for protocol in self.protocols:
                protocol.packetReceived(packet)

    def registerProtocol(self, protocol):
        if not self.connected:
            self.startReading()

        if protocol not in self.protocols:
            protocol.factory = self
            self.protocols.append(protocol)
        else:
            raise ProtocolAlreadyRegistered

    def unRegisterProtocol(self, protocol):
        if protocol in self.protocols:
            self.protocols.remove(protocol)
            if len(self.protocols) == 0:
                self.loseConnection()
        else:
            raise ProtocolNotRegistered

class ScapyProtocol(object):
    factory = None

    def packetReceived(self, packet):
        """
        When you register a protocol, this method will be called with argument
        the packet it received.

        Every protocol that is registered will have this method called.
        """
        raise NotImplementedError

class ScapySender(ScapyProtocol):
    timeout = 5

    # This deferred will fire when we have finished sending a receiving packets.
    # Should we look for multiple answers for the same sent packet?
    multi = False

    # When 0 we stop when all the packets we have sent have received an
    # answer
    expected_answers = 0

    def processPacket(self, packet):
        """
        Hook useful for processing packets as they come in.
        """

    def processAnswer(self, packet, answer_hr):
        log.debug("Got a packet from %s" % packet.src)
        log.debug("%s" % self.__hash__)
        for i in range(len(answer_hr)):
            if packet.answers(answer_hr[i]):
                self.answered_packets.append((answer_hr[i], packet))
                if not self.multi:
                    del(answer_hr[i])
                break

        if len(self.answered_packets) == len(self.sent_packets):
            log.debug("All of our questions have been answered.")
            self.stopSending()
            return

        if self.expected_answers and \
                self.expected_answers == len(self.answered_packets):
            log.debug("Got the number of expected answers")
            self.stopSending()

    def packetReceived(self, packet):
        timeout = time.time() - self._start_time
        if self.timeout and time.time() - self._start_time > self.timeout:
            self.stopSending()
        if packet:
            self.processPacket(packet)
            # A string that has the same value for the request than for the
            # response.
            hr = packet.hashret()
            if hr in self.hr_sent_packets:
                answer_hr = self.hr_sent_packets[hr]
                self.processAnswer(packet, answer_hr)

    def stopSending(self):
        result = (self.answered_packets, self.sent_packets)
        self.d.callback(result)
        self.factory.unRegisterProtocol(self)

    def sendPackets(self, packets):
        if not isinstance(packets, Gen):
            packets = SetGen(packets)
        for packet in packets:
            hashret = packet.hashret()
            if hashret in self.hr_sent_packets:
                self.hr_sent_packets[hashret].append(packet)
            else:
                self.hr_sent_packets[hashret] = [packet]
            self.sent_packets.append(packet)
            self.factory.send(packet)

    def startSending(self, packets):
        # This dict is used to store the unique hashes that allow scapy to
        # match up request with answer
        self.hr_sent_packets = {}

        # These are the packets we have received as answer to the ones we sent
        self.answered_packets = []

        # These are the packets we send
        self.sent_packets = []

        self._start_time = time.time()
        self.d = defer.Deferred()
        self.sendPackets(packets)
        return self.d

class ScapySniffer(ScapyProtocol):
    def __init__(self, pcap_filename, *arg, **kw):
        self.pcapwriter = PcapWriter(pcap_filename, *arg, **kw)

    def packetReceived(self, packet):
        self.pcapwriter.write(packet)

class ScapyTraceroute(ScapyProtocol):
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]
    ttl_min = 1
    ttl_max = 30

    def __init__(self):
        self.sent_packets = []
        self.received_packets = {}
        self.matched_packets = {}
        self.hosts = []

    def ICMPTraceroute(self, host):
        if host not in self.hosts: self.hosts.append(host)
        self.sendPackets(IP(dst=host,ttl=(self.ttl_min,self.ttl_max), id=RandShort())/ICMP(id=RandShort()))

    def UDPTraceroute(self, host):
        if host not in self.hosts: self.hosts.append(host)
        for dst_port in self.dst_ports:
            self.sendPackets(IP(dst=host,ttl=(self.ttl_min,self.ttl_max), id=RandShort())/UDP(dport=dst_port, sport=RandShort()))

    def TCPTraceroute(self, host):
        if host not in self.hosts: self.hosts.append(host)
        for dst_port in self.dst_ports:
            self.sendPackets(IP(dst=host,ttl=(self.ttl_min,self.ttl_max), id=RandShort())/TCP(flags=2L, dport=dst_port, sport=RandShort(), seq=RandShort()))

    def sendPackets(self, packets):
        #if random.randint(0,1):
        #    random.shuffle(packets)
        for packet in packets:
            self.sent_packets.append(packet)
            self.factory.super_socket.send(packet)

    def matchResponses(self):
        def _pe(k, p):
            if k in self.received_packets:
                if p in self.matched_packets:
                    log.debug("Matched sent packet to more than one response!")
                    self.matched_packets[p].extend(self.received_packets[k])
                else:
                    self.matched_packets[p] = self.received_packets[k]
                log.debug("Packet %s matched %s" % ([p], self.received_packets[k]))
                return 1
            return 0

        for p in self.sent_packets:
            # for each sent packet, find corresponding
            # received packets
            l = p.getlayer(1)
            i = 0
            if isinstance(l, ICMP):
                i += _pe((ICMP, p.id), p) # match by ipid
                i += _pe((ICMP, l.id), p) # match by icmpid
            if isinstance(l, TCP):
                i += _pe((TCP, p.id), p) # match by ipid
                i += _pe((TCP, p.id, l.seq, l.ack, l.sport, l.dport), p)
            if isinstance(l, UDP):
                i += _pe((UDP, p.id), p)
            if i == 0:
                log.debug("No response for packet %s" % [p])

    def packetReceived(self, packet):
        def _ae(k, p):
            if k in self.received_packets:
                self.received_packets[k].append(p)
            else:
                self.received_packets[k] = [p]

        l = packet.getlayer(2)
        try:
            if isinstance(l, IPerror):
                pid = l.id
                l = packet.getlayer(3)
                if isinstance(l, ICMPerror):
                    _ae((ICMP, pid), packet)
                elif isinstance(l, TCPerror):
                    _ae((TCP, pid, l.seq, l.ack, l.sport, l.dport), packet)
                elif isinstance(l, UDPerror):
                    _ae((UDP, pid), packet)
            elif packet.src in self.hosts:
                l = packet.getlayer(1)
                if isinstance(l, ICMP):
                    _ae((ICMP, l.id), packet)
                elif isinstance(l, TCP):
                    _ae((TCP, l.seq, l.ack, l.sport, l.dport), packet)
                elif isinstance(l, UDP):
                    _ae((UDP, l.sport, l.dport), packet)
        except Exception, e:
            import pdb;pdb.set_trace()

    def stopListening(self):
        self.factory.unRegisterProtocol(self)

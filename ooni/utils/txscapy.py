import sys
import time
import random
from twisted.internet import fdesc
from twisted.internet import reactor
from twisted.internet import defer, abstract

from scapy.config import conf
from scapy.all import RandShort, IP, IPerror, ICMP, ICMPerror, TCP, TCPerror, UDP, UDPerror

from ooni.errors import ProtocolNotRegistered, ProtocolAlreadyRegistered, LibraryNotInstalledError

from ooni.utils import log

from ooni.utils.net import getDefaultIface, getAddresses
from ooni.settings import config


# Check to see if libdnet or libpcap are installed and set the according
# variables.

# In debian libdnet is called dumbnet instead of dnet, but scapy is
# expecting "dnet" so we try and import it under such name.
try:
    import dumbnet

    sys.modules['dnet'] = dumbnet
except ImportError:
    pass

try:
    conf.use_pcap = True
    conf.use_dnet = True
    from scapy.arch import pcapdnet

    config.pcap_dnet = True

except ImportError as e:
    log.err(e.message + ". Pypcap or dnet are not properly installed. Certain tests may not work.")
    config.pcap_dnet = False
    conf.use_pcap = False
    conf.use_dnet = False

# This is required for unix systems that are different than linux (OSX for
# example) since scapy explicitly wants pcap and libdnet installed for it
# to work.
try:
    from scapy.arch import pcapdnet
except ImportError:
    log.err("Your platform requires having libdnet and libpcap installed.")
    raise LibraryNotInstalledError

_PCAP_DNET_INSTALLED = config.pcap_dnet

if _PCAP_DNET_INSTALLED:
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
            super_socket = conf.L3socket(iface=interface)

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
                    del (answer_hr[i])
                break

        if len(self.answered_packets) == len(self.sent_packets):
            log.debug("All of our questions have been answered.")
            self.stopSending()
            return

        if self.expected_answers and self.expected_answers == len(self.answered_packets):
            log.debug("Got the number of expected answers")
            self.stopSending()

    def packetReceived(self, packet):
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

    def close(self):
        self.pcapwriter.close()


class ParasiticTraceroute(ScapyProtocol):
    def __init__(self):
        self.numHosts = 7
        self.rate = 15
        self.hosts = {}
        self.ttl_max = 15
        self.ttl_min = 1
        self.sent_packets = []
        self.received_packets = []
        self.matched_packets = {}
        self.addresses = [str(x) for x in getAddresses()]

    def sendPacket(self, packet):
        self.factory.send(packet)
        self.sent_packets.append(packet)
        log.debug("Sent packet to %s with ttl %d" % (packet.dst, packet.ttl))

    def packetReceived(self, packet):
        try:
            packet[IP]
        except IndexError:
            return

        # Add TTL Expired responses.
        if isinstance(packet.getlayer(3), TCPerror):
            self.received_packets.append(packet)
            # Live traceroute?
            log.debug("%s replied with icmp-ttl-exceeded for %s" % (packet.src, packet[IPerror].dst))
            return
        elif packet.dst in self.hosts:
            if random.randint(1, 100) > self.rate:
                # Don't send a packet this time
                return
            try:
                packet[IP].ttl = self.hosts[packet.dst]['ttl'].pop()
                del packet.chksum  # XXX Why is this incorrect?
                self.sendPacket(packet)
                k = (packet.id, packet[TCP].sport, packet[TCP].dport, packet[TCP].seq)
                self.matched_packets[k] = {'ttl': packet.ttl}
                return
            except IndexError:
                return

        def maxttl(packet=None):
            if packet:
                return min(self.ttl_max, *map(lambda x: x - packet.ttl, [64, 128, 256])) - 1
            else:
                return self.ttl_max

        def genttl(packet=None):
            ttl = range(self.ttl_min, maxttl(packet))
            random.shuffle(ttl)
            return ttl

        if len(self.hosts) < self.numHosts:
            if packet.dst not in self.hosts \
                    and packet.dst not in self.addresses \
                    and isinstance(packet.getlayer(1), TCP):

                self.hosts[packet.dst] = {'ttl': genttl()}
                log.debug("Tracing to %s" % packet.dst)
                return
            if packet.src not in self.hosts \
                    and packet.src not in self.addresses \
                    and isinstance(packet.getlayer(1), TCP):
                self.hosts[packet.src] = {'ttl': genttl(packet),
                                          'ttl_max': maxttl(packet)}
                log.debug("Tracing to %s" % packet.src)
                return

        if packet.src in self.hosts and not 'ttl_max' in self.hosts[packet.src]:
            self.hosts[packet.src]['ttl_max'] = ttl_max = maxttl(packet)
            log.debug("set ttl_max to %d for host %s" % (ttl_max, packet.src))
            ttl = []
            for t in self.hosts[packet.src]['ttl']:
                if t < ttl_max:
                    ttl.append(t)
            self.hosts[packet.src]['ttl'] = ttl
            return

    def stopListening(self):
        self.factory.unRegisterProtocol(self)


class MPTraceroute(ScapyProtocol):
    dst_ports = [0, 22, 23, 53, 80, 123, 443, 8080, 65535]
    ttl_min = 1
    ttl_max = 30

    def __init__(self):
        self.sent_packets = []
        self._recvbuf = []
        self.received_packets = {}
        self.matched_packets = {}
        self.hosts = []
        self.interval = 0.2
        self.timeout = ((self.ttl_max - self.ttl_min) * len(self.dst_ports) * self.interval) + 5
        self.numPackets = 1

    def ICMPTraceroute(self, host):
        if host not in self.hosts:
            self.hosts.append(host)

        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self)

        self.sendPackets(IP(dst=host, ttl=(self.ttl_min, self.ttl_max), id=RandShort()) / ICMP(id=RandShort()))
        return d

    def UDPTraceroute(self, host):
        if host not in self.hosts:
            self.hosts.append(host)

        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self)

        for dst_port in self.dst_ports:
            self.sendPackets(
                IP(dst=host, ttl=(self.ttl_min, self.ttl_max), id=RandShort()) / UDP(dport=dst_port, sport=RandShort()))
        return d

    def TCPTraceroute(self, host):
        if host not in self.hosts:
            self.hosts.append(host)

        d = defer.Deferred()
        reactor.callLater(self.timeout, d.callback, self)

        for dst_port in self.dst_ports:
            self.sendPackets(
                IP(dst=host, ttl=(self.ttl_min, self.ttl_max), id=RandShort()) / TCP(flags=2L, dport=dst_port,
                                                                                     sport=RandShort(),
                                                                                     seq=RandShort()))
        return d

    @defer.inlineCallbacks
    def sendPackets(self, packets):
        def sleep(seconds):
            d = defer.Deferred()
            reactor.callLater(seconds, d.callback, seconds)
            return d

        if not isinstance(packets, Gen):
            packets = SetGen(packets)

        for packet in packets:
            for i in xrange(self.numPackets):
                self.sent_packets.append(packet)
                self.factory.super_socket.send(packet)
                yield sleep(self.interval)

    def matchResponses(self):
        def addToReceivedPackets(key, packet):
            """
            Add a packet into the received packets dictionary,
            typically the key is a tuple of packet fields used
            to correlate sent packets with received packets.
            """

            # Initialize or append to the lists of packets
            # with the same key
            if key in self.received_packets:
                self.received_packets[key].append(packet)
            else:
                self.received_packets[key] = [packet]

        def matchResponse(k, p):
            if k in self.received_packets:
                if p in self.matched_packets:
                    log.debug("Matched sent packet to more than one response!")
                    self.matched_packets[p].extend(self.received_packets[k])
                else:
                    self.matched_packets[p] = self.received_packets[k]
                log.debug("Packet %s matched %s" % ([p], self.received_packets[k]))
                return 1
            return 0

        for p in self._recvbuf:
            l = p.getlayer(2)
            if isinstance(l, IPerror):
                l = p.getlayer(3)
                if isinstance(l, ICMPerror):
                    addToReceivedPackets(('icmp', l.id), p)
                elif isinstance(l, TCPerror):
                    addToReceivedPackets(('tcp', l.dport, l.sport), p)
                elif isinstance(l, UDPerror):
                    addToReceivedPackets(('udp', l.dport, l.sport), p)
            elif hasattr(p, 'src') and p.src in self.hosts:
                l = p.getlayer(1)
                if isinstance(l, ICMP):
                    addToReceivedPackets(('icmp', l.id), p)
                elif isinstance(l, TCP):
                    addToReceivedPackets(('tcp', l.ack - 1, l.dport, l.sport), p)
                elif isinstance(l, UDP):
                    addToReceivedPackets(('udp', l.dport, l.sport), p)

        for p in self.sent_packets:
            # for each sent packet, find corresponding
            # received packets
            l = p.getlayer(1)
            i = 0
            if isinstance(l, ICMP):
                i += matchResponse(('icmp', p.id), p)  # match by ipid
                i += matchResponse(('icmp', l.id), p)  # match by icmpid
            if isinstance(l, TCP):
                i += matchResponse(('tcp', l.dport, l.sport), p)  # match by s|dport
                i += matchResponse(('tcp', l.seq, l.sport, l.dport), p)
            if isinstance(l, UDP):
                i += matchResponse(('udp', l.dport, l.sport), p)
                i += matchResponse(('udp', l.sport, l.dport), p)
            if i == 0:
                log.debug("No response for packet %s" % [p])

        del self._recvbuf

    def packetReceived(self, packet):
        l = packet.getlayer(1)
        if not l:
            return
        elif isinstance(l, ICMP) or isinstance(l, UDP) or isinstance(l, TCP):
            self._recvbuf.append(packet)

    def stopListening(self):
        self.factory.unRegisterProtocol(self)

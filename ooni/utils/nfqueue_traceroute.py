#!/usr/bin/env python

# Internal modules
from ooni.utils.txscapy import ScapyProtocol
from ooni.utils.nfqueue_reader import NFQueueReader

# External modules
from scapy.all import IP, TCP


class NFQueueTraceroute(ScapyProtocol):

    """
    MITM parasitic traceroute.
    First draft will be TCP only.
    No reason it couldn't be multi-protocol.
    """

    ttl_min = 1
    ttl_max = 30 # XXX is this a good upper limit?

    def __init__(self, nqueue=0, tcp_streams_to_mangle=[]):
        """
        nqueue indicates which NFQUEUE we should mangle packets from.
        tcp_streams_to_mangle is a list of 4-tuples
        (src_addr, src_port, dst_addr, dst_port)
        which uniquely identify the TCP stream(s) to mangle.
        """

        self.nqueue = nqueue

        # used to keep track of the last mangled TTL for each stream
        # keyed with TCP 4-tuple
        # value is last mangled TTL
        self.stream_last_mangled_ttl = {}

        # use this to determine hop count of ICMP errors
        # by keeping track of the mangled TTL for corresponding
        # TCP sequence number
        # 
        # outer dict keyed with TCP 4-tuple
        # value is inner dict
        # inner dict keyed with TCP sequence number
        # inner dict value is mangled TTL
        self.mangle_streams = {}

        # Firstly, initialize all stream dicts to empty dict.
        for stream_id in tcp_streams_to_mangle:
            assert stream_id not in self.mangle_streams
            assert len(stream_id) == 4
            # XXX perhaps sanity check stream_id format?

            self.mangle_streams[stream_id] = {}

            # start off with mangled TTL of 1
            self.stream_last_mangled_ttl[stream_id] = 1

        self.nfqueue_reader = NFQueueReader(self.handleNFQueuePacket, nqueue=self.nqueue)

    def startTraceroute(self):
        """To be called from the test class"""
        reactor.addReader(self.nfqueue_reader)

    def stopListening(self):
        reactor.removeReader(self.nfqueue_reader)
        self.factory.unRegisterProtocol(self)

    def handleNFQueuePacket(self, queue_item):
        ip_packet = IP(queue_item.get_data())
        if self.isMangleStream(ip_packet):
            self.manglePacket(queue_item, ip_packet)

    def isMangleStream(self, ip_packet):
        """
        Return True or False depending on if
        streamID is in our self.mangleStream dict
        """
        streamID  = ip_packet.src, ip_packet[TCP].sport, ip_packet.dst, ip_packet[TCP].dport
        if streamID in self.mangleStream:
            return True
        else:
            return False

    def manglePacket(self, queue_item, ip_packet):
        """mangle TCP packet TTL"""

        # XXX later i need to develope more heuristics for deciding
        # when to mangle packets...
        # For now we mangle all packets that are keyed in self.mangle_streams

        streamID = ip_packet.src, ip_packet[TCP].sport, ip_packet.dst, ip_packet[TCP].dport        

        # keep track of last mangled TTL
        self.stream_last_mangled_ttl[stream_id] += 1
        new_ttl = self.stream_last_mangled_ttl[stream_id]
        ip_packet.ttl = new_ttl
        del ip_packet.chksum

        # keep track of mangled TTL per TCP sequence number
        sequenceNum = ip_packet[TCP].seq
        self.mangle_streams[streamID][sequenceNum] = new_ttl

        queue_item.set_verdict_modified(nfqueue.NF_ACCEPT, str(ip_packet), len(ip_packet))

    def packetReceived(self, packet):
        try:
            packet[IP]
        except IndexError:
            return

        if isinstance(packet.getlayer(3), TCPerror):
            self.received_packets.append(packet)
            return


class NFQueueTracerouteTest(scapyt.BaseScapyTest):
# XXX should I use scapyt.BaseScapyTest or write something else?

    name = "NFQueue TCP Traceroute Test"
    description = "Performs a local MITM on specified TCP streams. Packets are intercepted and the TTLs are mangled before going out the network interface. We can thereby use this to cause any TCP stream (server or client) to perform a traceroute."

    def setUp(self):

        # XXX fix this bullshit
        streamIDs = [ (src_addr, src_port, dst_addr, dst_port) ]

        self.st = NFQueueTraceroute(nqueue=0, tcp_streams_to_mangle=streamIDs)
        config.scapyFactory.registerProtocol(self.st)

        self.report['NFQueueTracerouteTest'] = {}
        

    def test_nfqueue_traceroute(self):
        # XXX should i be returning a deferred?
        return self.st.startTraceroute()

    def postProcessor(self, measurements):
        # should be called after all deferreds have calledback
        self.st.stopListening()
        self.st.matchResponses()

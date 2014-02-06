#!/usr/bin/env python

# Internal modules
from nfqueue_reader import NFQueueReader

# External modules
import nfqueue
from scapy.all import IP, IPerror, TCP, TCPerror, ICMP
from twisted.internet import reactor, task

class StreamTracker(object):

    max_ttl = 30

    def __init__(self):
        self.last_ttl = 0

        # keyed with TCP sequence number + IP ID
        # value is TTL
        self.ttls     = {}
        #self.packets  = {}

        self.packet_count = 0

    def processPacket(self, queue_item, packet):

        assert TCPerror not in packet
        assert IPerror not in packet
        assert ICMP not in packet

        # keep track of mangled TTL per TCP sequence number
        sequenceNum = packet[TCP].seq

        if sequenceNum in self.ttls:
            # we've already seen this sequence number
            # don't mangle TCP retransmits
            queue_item.set_verdict(nfqueue.NF_ACCEPT)
        else:
            self.last_ttl += 1

            if self.last_ttl > self.max_ttl:
                self.last_ttl = 1

            packet.ttl     = self.last_ttl
            del packet.chksum
            self.ttls[sequenceNum]    = self.last_ttl
            #self.packets[sequenceNum] = packet
            queue_item.set_verdict_modified(nfqueue.NF_ACCEPT, str(packet), len(packet))


class NFQueueTraceroute(object):

    """
    MITM parasitic traceroute.
    First draft will be TCP only.
    No reason it couldn't be multi-protocol.
    """

    ttl_min = 1
    ttl_max = 30 # XXX is this a good upper limit?

    def __init__(self, nqueue=0):
        """
        nqueue indicates which NFQUEUE we should mangle packets from
        AND
        where we also receive ICMP packets (e.g. TTL expired)
        """

        self.nqueue = nqueue

        # dict keyed with TCP 4-tuple
        # value is a StreamTracker
        self.mangled_streams = {}

        self.nfqueue_reader = NFQueueReader(self.handleNFQueuePacket, nqueue=self.nqueue)

        # interesting things to report
        self.report       = {}
        self.error_report = {}

    def start(self):
        reactor.addReader(self.nfqueue_reader)

    def stop(self):
        reactor.removeReader(self.nfqueue_reader)

    def printReport(self):

        for stream_id in self.report:
            print "\ntraceroute for " + str(stream_id)
            # sort by ttl
            for hop in sorted( self.report[stream_id], key=lambda x: x[0] ):
                print hop

    def handleNFQueuePacket(self, queue_item):
        packet = IP(queue_item.get_data())

        if IPerror in packet:
            self.handleICMP(queue_item, packet)
        else:
            stream_id = self.getStreamID(packet)

            if stream_id not in self.mangled_streams:
                self.mangled_streams[stream_id] = StreamTracker()

            self.mangled_streams[stream_id].processPacket(queue_item, packet)

    # given a scapy IP/TCP packet return a
    # stream ID... a TCP 4-tuple
    def getStreamID(self, packet):
        if TCPerror in packet:
            return packet.src, packet[TCPerror].sport, packet.dst, packet[TCPerror].dport
        else:
            return packet.src, packet[TCP].sport, packet.dst, packet[TCP].dport

    def handleICMP(self, queue_item, packet):
        """get TCP sequence number
        and figure out the mangled TTL
        value we used to produce this ICMP error...
        """

        sequence_num = packet[ICMP].payload[TCPerror].seq
        stream_id    = self.getStreamID(packet[ICMP].payload)

        if stream_id in self.mangled_streams:
            mangled_ttl = self.mangled_streams[stream_id].ttls[sequence_num]

            if stream_id in self.report:
                self.report[stream_id].append( (mangled_ttl, packet.src) )
            else:
                self.report[stream_id] = [ (mangled_ttl, packet.src) ]

        else:
            # XXX what should we do with ICMP packets we weren't expecting?
            self.error_report[(stream_id, sequence_num)] = packet

        # it should not matter if we drop or accept
        #queue_item.set_verdict(nfqueue.NF_DROP)
        queue_item.set_verdict(nfqueue.NF_ACCEPT)


# make sure you have a rule for the ICMP packets
# iptables -A INPUT -p icmp -j NFQUEUE --queue-num 0
#
# and a rule for the TCP packets
# something like this:
# iptables -A OUTPUT -p tcp -m state --state RELATED,ESTABLISHED --dport 443 -m statistic --mode random --probability 0.1 -j NFQUEUE --queue-num 0
# OR this:
# iptables -A OUTPUT -p tcp -m state --state RELATED,ESTABLISHED --dport 443 -j NFQUEUE --queue-num 0


def main():

    nfqueue_traceroute = NFQueueTraceroute()
    nfqueue_traceroute.start()

    d = task.deferLater(reactor, 60, lambda ignored: nfqueue_traceroute.stop(), None)
    d.addCallback(lambda ignored: nfqueue_traceroute.printReport())
    d.addCallback(lambda ignored: reactor.stop())

    reactor.run()
 
if __name__ == "__main__":
    main()


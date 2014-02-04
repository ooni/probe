#!/usr/bin/env python

# Internal modules
from nfqueue_reader import NFQueueReader

# External modules
import nfqueue
from scapy.all import IP, IPerror, TCP, TCPerror, ICMP
from twisted.internet import reactor

class StreamTracker(object):

    max_ttl = 30

    def __init__(self):
        self.last_ttl = 1

        # XXX not yet used
        # could be keyed with TCP sequence number + IP ID?
        self.packets  = {}

        # keyed with TCP sequence number
        # value is TTL
        self.ttls     = {}

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
            print "%s previously seen" % sequenceNum
        else:
            print "%s NOT previously seen" % sequenceNum
            print "last_ttl %s" % self.last_ttl

            self.last_ttl += 1

            if self.last_ttl > self.max_ttl:
                self.last_ttl = 1

            packet.ttl     = self.last_ttl
            del packet.chksum
            self.ttls[sequenceNum] = self.last_ttl
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
        print self.report
        reactor.stop()

    def handleNFQueuePacket(self, queue_item):
        packet = IP(queue_item.get_data())

        if IPerror in packet:
            print "ICMP"
            self.handleICMP(queue_item, packet)
        else:
            print "IP"
            stream_id = self.getStreamID(packet)

            if stream_id not in self.mangled_streams:
                print "new stream"
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

        print "handleICMP"

        sequence_num = packet[ICMP].payload[TCPerror].seq
        stream_id    = self.getStreamID(packet[ICMP].payload)

        print "%s %s" % (sequence_num, stream_id)

        if stream_id in self.mangled_streams:
            mangled_ttl = self.mangled_streams[stream_id].ttls[sequence_num]
            self.report[(stream_id, sequence_num)] = mangled_ttl
        else:
            self.error_report[(stream_id, sequence_num)] = packet

        # XXX does it even matter if we accept or deny here?
        queue_item.set_verdict(nfqueue.NF_DROP)



# iptables -A OUTPUT -p tcp -m state --state RELATED,ESTABLISHED --dport 443 -j NFQUEUE --queue-num 0
# iptables -A INPUT -p icmp -j NFQUEUE --queue-num 0

def main():

    nfqueue_traceroute = NFQueueTraceroute()
    nfqueue_traceroute.start()

    reactor.callLater(30, lambda:nfqueue_traceroute.stop())
    reactor.run()
 
if __name__ == "__main__":
    main()


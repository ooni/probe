#!/usr/bin/env python

# External modules
from twisted.internet import reactor
from zope.interface import implements
from twisted.internet.interfaces import IReadDescriptor

from socket import AF_INET
import nfqueue

from scapy.all import IP, TCP



class NFQueueReader(object):

    implements(IReadDescriptor)
    
    def __init__(self, cb, nqueue=0, family=AF_INET, maxlen=50000):
        self.maxlen = maxlen
        self.queue  = nfqueue.queue()

        self.queue.set_callback(cb)
        self.queue.fast_open(nqueue, family)
        self.queue.set_queue_maxlen(maxlen)

        self.fd     = self.queue.get_fd()
        self.queue.set_mode(nfqueue.NFQNL_COPY_PACKET)

    def fileno(self):
        return self.fd

    def doRead(self):
        self.queue.process_pending(self.maxlen)

    def connectionLost(self, reason):
        reactor.removeReader(self)

    def logPrefix(self):
        return 'NFQueueReader'



# code to test with
# iptables -A OUTPUT -p tcp --dport 443 -j NFQUEUE --queue-num 0

def main():

    packet_count = [0]

    def callback(queue_item):
        packet_count[0] += 1
        
        ip_packet = IP(queue_item.get_data())

        if packet_count[0] > 10 and packet_count[0] % 5 == 0:
            ip_packet.ttl = 0
            del ip_packet.chksum

        #print ip_packet.show()
        queue_item.set_verdict_modified(nfqueue.NF_ACCEPT, str(ip_packet), len(ip_packet))
        

    nfqueue_reader = NFQueueReader(callback)
    reactor.addReader(nfqueue_reader)


    reactor.run()
 
if __name__ == "__main__":
    main()


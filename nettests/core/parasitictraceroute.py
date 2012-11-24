# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage
from twisted.internet import defer

from ooni.templates import scapyt

from scapy.all import *

from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', 'google.com', 'Test backend to use'],
                    ['timeout', 't', 5, 'The timeout for the traceroute test'],
                    ['maxttl', 'm', 64, 'The maximum value of ttl to set on packets'],
                    ['dstport', 'd', 80, 'Set the destination port of the traceroute test'],
                    ['srcport', 'p', None, 'Set the source port to a specific value']]

class ParasiticalTracerouteTest(scapyt.BaseScapyTest):
    name = "Parasitic TCP Traceroute Test"
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    def setUp(self):
        def get_sport():
            if self.localOptions['srcport']:
                return int(self.localOptions['srcport'])
            else:
                return random.randint(1024, 65535)
        self.get_sport = get_sport

        self.dst_ip = socket.gethostbyaddr(self.localOptions['backend'])[2][0]

        self.dport = int(self.localOptions['dstport'])
        self.max_ttl = int(self.localOptions['maxttl'])

    @defer.inlineCallbacks
    def test_parasitic_tcp_traceroute(self):
        """
        Establishes a TCP stream, then sequentially sends TCP packets with
        increasing TTL until we reach the ttl of the destination.

        Requires the backend to respond with an ACK to our SYN packet (i.e.
        the port must be open)

        XXX this currently does not work properly. The problem lies in the fact
        that we are currently using the scapy layer 3 socket. This socket makes
        packets received be trapped by the kernel TCP stack, therefore when we
        send out a SYN and get back a SYN-ACK the kernel stack will reply with
        a RST because it did not send a SYN.

        The quick fix to this would be to establish a TCP stream using socket
        calls and then "cannibalizing" the TCP session with scapy.

        The real fix is to make scapy use libpcap instead of raw sockets
        obviously as we previously did... arg.
        """
        sport = self.get_sport()
        dport = self.dport
        ipid = int(RandShort())

        ip_layer = IP(dst=self.dst_ip,
                id=ipid, ttl=self.max_ttl)

        syn = ip_layer/TCP(sport=sport, dport=dport, flags="S", seq=0)

        log.msg("Sending...")
        syn.show2()

        synack = yield self.sr1(syn)

        log.msg("Got response...")
        synack.show2()

        if not synack:
            log.err("Got no response. Try increasing max_ttl")
            return

        if synack[TCP].flags == 11:
            log.msg("Got back a FIN ACK. The destination port is closed")
            return

        elif synack[TCP].flags == 18:
            log.msg("Got a SYN ACK. All is well.")
        else:
            log.err("Got an unexpected result")
            return

        ack = ip_layer/TCP(sport=synack.dport,
                            dport=dport, flags="A",
                            seq=synack.ack, ack=synack.seq + 1)

        yield self.send(ack)

        self.report['hops'] = []
        # For the time being we make the assumption that we are NATted and
        # that the NAT will forward the packet to the destination even if the TTL has 
        for ttl in range(1, self.max_ttl):
            log.msg("Sending packet with ttl of %s" % ttl)
            ip_layer.ttl = ttl
            empty_tcp_packet = ip_layer/TCP(sport=synack.dport,
                    dport=dport, flags="A",
                    seq=synack.ack, ack=synack.seq + 1)

            answer = yield self.sr1(empty_tcp_packet)
            if not answer:
                log.err("Got no response for ttl %s" % ttl)
                continue

            try:
                icmp = answer[ICMP]
                report = {'ttl': empty_tcp_packet.ttl,
                    'address': answer.src,
                    'rtt': answer.time - empty_tcp_packet.time
                }
                log.msg("%s: %s" % (dport, report))
                self.report['hops'].append(report)

            except IndexError:
                if answer.src == self.dst_ip:
                    answer.show()
                    log.msg("Reached the destination. We have finished the traceroute")
                    return


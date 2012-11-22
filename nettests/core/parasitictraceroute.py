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
    optParameters = [['backend', 'b', '8.8.8.8', 'Test backend to use'],
                    ['timeout', 't', 5, 'The timeout for the traceroute test'],
                    ['maxttl', 'm', 30, 'The maximum value of ttl to set on packets'],
                    ['dstport', 'd', 80, 'Set the destination port of the traceroute test'],
                    ['srcport', 'p', None, 'Set the source port to a specific value']]

    optFlags = [['randomize','r', 'Randomize the source port']]

class TracerouteTest(scapyt.BaseScapyTest):
    name = "Parasitic TCP Traceroute Test"
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    def setUp(self):
        def get_sport():
            if self.localOptions['srcport']:
                return int(self.localOptions['srcport'])
            elif self.localOptions['randomize']:
                return random.randint(1024, 65535)
            else:
                return 80

        self.get_sport = get_sport
        self.dport = int(self.localOptions['dstport'])

    def max_ttl_and_timeout(self):
        max_ttl = int(self.localOptions['maxttl'])
        timeout = int(self.localOptions['timeout'])
        self.report['max_ttl'] = max_ttl
        self.report['timeout'] = timeout
        return max_ttl, timeout

    @defer.inlineCallbacks
    def test_parasitic_tcp_traceroute(self):
        """
        Establishes a TCP stream and send the packets inside of such stream.
        Requires the backend to respond with an ACK to our SYN packet.
        """
        max_ttl, timeout = self.max_ttl_and_timeout()

        sport = self.get_sport()
        dport = self.dport
        ipid = int(RandShort())

        packet = IP(dst=self.localOptions['backend'], ttl=max_ttl,
                id=ipid)/TCP(sport=sport, dport=dport,
                        flags="S", seq=0)

        log.msg("Sending SYN towards %s" % dport)

        try:
            answered, unanswered = yield self.sr(packet, timeout=timeout)
        except Exception, e:
            log.exception(e)
        except:
            log.exception()

        try:
            snd, rcv = answered[0]
            synack = rcv[0]

        except IndexError:
            print answered, unanswered
            log.err("Got no response. Try increasing max_ttl")
            return

        except Exception, e:
            log.exception(e)

        if synack[TCP].flags == 11:
            log.msg("Got back a FIN ACK. The destination port is closed")
            return

        elif synack[TCP].flags == 18:
            log.msg("Got a SYN ACK. All is well.")
        else:
            log.err("Got an unexpected result")

        self.report['hops'] = []
        for ttl in range(1, max_ttl):
            log.msg("Sending ACK with ttl %s" % ttl)
            # We generate an ack for the syn-ack we got with increasing ttl
            packet = IP(dst=self.localOptions['backend'],
                    ttl=ttl, id=ipid)/TCP(sport=synack.dport,
                            dport=dport, flags="A",
                            seq=synack.ack, ack=synack.seq + 1)

            answered, unanswered = yield self.sr(packet, timeout=timeout)
            try:
                snd, rcv = answered[0]
            except IndexError:
                log.err("Got no response.")

            try:
                icmp = rcv[ICMP]

            except IndexError:
                report = {'ttl': snd.ttl,
                        'address': rcv.src,
                        'rtt': rcv.time - snd.time
                }
                log.debug("%s: %s" % (dport, report))
                self.report['hops'].append(report)
                if rcv.src == self.localOptions['backend']:
                    log.msg("Reached the destination. We have finished the traceroute")
                    return


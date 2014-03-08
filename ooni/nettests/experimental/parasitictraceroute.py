from twisted.python import usage
from twisted.internet import defer, reactor
from ooni.templates import scapyt
from ooni.utils import log
from ooni.utils.txscapy import ParasiticTraceroute
from ooni.settings import config

from scapy.all import TCPerror, IPerror

class ParasiticTracerouteTest(scapyt.BaseScapyTest):
    name = "Parasitic Traceroute Test"
    description = "Injects duplicate TCP packets with varying TTL values by sniffing traffic"
    version = '0.1'

    samplePeriod = 40
    requiresTor = False
    requiresRoot = False

    def setUp(self):
        self.report['parasitic_traceroute'] = {}

    def test_parasitic_traceroute(self):
        self.pt = ParasiticTraceroute()
        config.scapyFactory.registerProtocol(self.pt)
        d = defer.Deferred()
        reactor.callLater(self.samplePeriod, d.callback, self.pt)
        return d

    def postProcessor(self, *args, **kwargs):
        self.pt.stopListening()
        self.report['received_packets'] = self.pt.received_packets

        for packet in self.pt.received_packets:
            k = (packet[IPerror].id, packet[TCPerror].sport, packet[TCPerror].dport, packet[TCPerror].seq)
            if k in self.pt.matched_packets:
                ttl = self.pt.matched_packets[k]['ttl']
            else:
                ttl = 'unknown'
            hop = (ttl, packet.src)
            path = 'hops_%s' % packet[IPerror].dst
            if path in self.report['parasitic_traceroute']:
               self.report['parasitic_traceroute'][path].append(hop)
            else:
               self.report['parasitic_traceroute'][path] = [hop]
        for p in self.report['parasitic_traceroute'].keys():
            self.report['parasitic_traceroute'][p].sort(key=lambda x: x[0])
                
        self.report['sent_packets'] = self.pt.sent_packets
        return self.report


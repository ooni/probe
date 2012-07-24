import random
import string
import struct
import time

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import protocol, defer
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.utils import log
from ooni.protocols.scapyproto import ScapyTest

from ooni.lib.txscapy import txsr, txsend

class scapyArgs(usage.Options):
    optParameters = [['dst', 'd', None, 'Specify the target address'],
                     ['port', 'p', None, 'Specify the target port'],
                     ['pcap', 'f', None, 'The pcap file to write with the sent and received packets'],
                    ]

class ChinaTriggerTest(ScapyTest):
    """
    This test is a OONI based implementation of the C tool written
    by Philipp Winter to engage chinese probes in active scanning.

    Example of running it:
    ./ooni/ooniprobe.py chinatrigger -d 127.0.0.1 -p 8080 -f bla.pcap
    """
    implements(IPlugin, ITest)

    shortName = "chinatrigger"
    description = "Triggers the chinese probes into scanning"
    requirements = ['root']
    options = scapyArgs
    blocking = False

    receive = True
    pcapfile = 'example_scapy.pcap'
    timeout = 5

    def initialize(self, reactor=None):
        if not self.reactor:
            from twisted.internet import reactor
            self.reactor = reactor

    @staticmethod
    def set_random_servername(pkt):
        ret = pkt[:121]
        for i in range(16):
            ret += random.choice(string.ascii_lowercase)
        ret += pkt[121+16:]
        return ret

    @staticmethod
    def set_random_time(pkt):
        ret = pkt[:11]
        ret += struct.pack('!I', int(time.time()))
        ret += pkt[11+4:]
        return ret

    @staticmethod
    def set_random_field(pkt):
        ret = pkt[:15]
        for i in range(28):
            ret += chr(random.randint(0, 256))
        ret += pkt[15+28:]
        return ret

    @staticmethod
    def mutate(pkt, idx):
        """
        Slightly changed mutate function.
        """
        ret = pkt[:idx-1]
        mutation = chr(random.randint(0, 256))
        while mutation == pkt[idx]:
            mutation = chr(random.randint(0, 256))
        ret += mutation
        ret += pkt[idx:]
        return ret

    @staticmethod
    def set_all_random_fields(pkt):
        pkt = ChinaTriggerTest.set_random_servername(pkt)
        pkt = ChinaTriggerTest.set_random_time(pkt)
        pkt = ChinaTriggerTest.set_random_field(pkt)
        return pkt

    def build_packets(self, *args, **kw):
        """
        Override this method to build scapy packets.
        """
        from scapy.all import IP, TCP
        pkt = "\x16\x03\x01\x00\xcc\x01\x00\x00\xc8"\
              "\x03\x01\x4f\x12\xe5\x63\x3f\xef\x7d"\
              "\x20\xb9\x94\xaa\x04\xb0\xc1\xd4\x8c"\
              "\x50\xcd\xe2\xf9\x2f\xa9\xfb\x78\xca"\
              "\x02\xa8\x73\xe7\x0e\xa8\xf9\x00\x00"\
              "\x3a\xc0\x0a\xc0\x14\x00\x39\x00\x38"\
              "\xc0\x0f\xc0\x05\x00\x35\xc0\x07\xc0"\
              "\x09\xc0\x11\xc0\x13\x00\x33\x00\x32"\
              "\xc0\x0c\xc0\x0e\xc0\x02\xc0\x04\x00"\
              "\x04\x00\x05\x00\x2f\xc0\x08\xc0\x12"\
              "\x00\x16\x00\x13\xc0\x0d\xc0\x03\xfe"\
              "\xff\x00\x0a\x00\xff\x01\x00\x00\x65"\
              "\x00\x00\x00\x1d\x00\x1b\x00\x00\x18"\
              "\x77\x77\x77\x2e\x67\x6e\x6c\x69\x67"\
              "\x78\x7a\x70\x79\x76\x6f\x35\x66\x76"\
              "\x6b\x64\x2e\x63\x6f\x6d\x00\x0b\x00"\
              "\x04\x03\x00\x01\x02\x00\x0a\x00\x34"\
              "\x00\x32\x00\x01\x00\x02\x00\x03\x00"\
              "\x04\x00\x05\x00\x06\x00\x07\x00\x08"\
              "\x00\x09\x00\x0a\x00\x0b\x00\x0c\x00"\
              "\x0d\x00\x0e\x00\x0f\x00\x10\x00\x11"\
              "\x00\x12\x00\x13\x00\x14\x00\x15\x00"\
              "\x16\x00\x17\x00\x18\x00\x19\x00\x23"\
              "\x00\x00"

        pkt = ChinaTriggerTest.set_all_random_fields(pkt)
        pkts = [IP(dst=self.dst)/TCP(dport=self.port)/pkt]
        for x in range(len(pkt)):
            mutation = IP(dst=self.dst)/TCP(dport=self.port)/ChinaTriggerTest.mutate(pkt, x)
            pkts.append(mutation)
        return pkts

    def load_assets(self):
        if self.local_options:
            self.dst = self.local_options['dst']
            self.port = int(self.local_options['port'])
            if self.local_options['pcap']:
                self.pcapfile = self.local_options['pcap']
            if not self.port or not self.dst:
                pass

        return {}

chinatrigger = ChinaTriggerTest(None, None, None)


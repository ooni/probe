# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage

from ooni.templates import scapyt

from scapy.layers.inet import TCP, IP
from scapy.volatile import RandShort


class UsageOptions(usage.Options):
    optParameters = [
        ['backend', 'b', '127.0.0.1:57002', 'Test backend running TCP echo'],
        ['timeout', 't', 5, 'Timeout after which to give up waiting for RST packets']
    ]


class KeywordFiltering(scapyt.BaseScapyTest):
    name = "Keyword Filtering detection based on RST packets"
    author = "Arturo Filastò"
    version = "0.2"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'List of keywords to use for censorship testing']
    requiresRoot = True
    requiresTor = False

    def test_tcp_keyword_filtering(self):
        """
        Places the keyword to be tested in the payload of a TCP packet.
        XXX need to implement bisection method for enumerating keywords.
            though this should not be an issue since we are testing all 
            the keywords in parallel.
        """
        backend_ip, backend_port = self.localOptions['backend'].split(':')
        timeout = int(self.localOptions['timeout'])
        keyword_to_test = str(self.input)
        packets = IP(dst=backend_ip, id=RandShort()) / TCP(sport=4000, dport=int(backend_port)) / keyword_to_test
        d = self.sr(packets, timeout=timeout)

        @d.addCallback
        def finished(packets):
            answered, unanswered = packets
            self.report['rst_packets'] = []
            for snd, rcv in answered:
                # The received packet has the RST flag
                if rcv[TCP].flags == 4:
                    self.report['rst_packets'].append(rcv)
        return d


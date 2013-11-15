# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from twisted.python import usage
from twisted.internet import defer

from ooni.utils import log
from ooni.templates import scapyt

from scapy.all import *

class UsageOptions(usage.Options):
    optParameters = [
                    ['backend', 'b', '127.0.0.1:57002', 'Test backend running TCP echo'],
                    ['timeout', 't', 5, 'Timeout after which to give up waiting for RST packets']
                    ]

class KeywordFiltering(scapyt.BaseScapyTest):
    name = "Keyword Filtering detection based on RST packets"
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, 
            'List of keywords to use for censorship testing']

    def test_tcp_keyword_filtering(self):
        """
        Places the keyword to be tested in the payload of a TCP packet.
        XXX need to implement bisection method for enumerating keywords.
            though this should not be an issue since we are testing all 
            the keywords in parallel.
        """
        def finished(packets):
            log.debug("Finished running TCP traceroute test on port %s" % port)
            answered, unanswered = packets
            self.report['rst_packets'] = []
            for snd, rcv in answered:
                # The received packet has the RST flag
                if rcv[TCP].flags == 4:
                    self.report['rst_packets'].append(rcv)

        backend_ip, backend_port = self.localOptions['backend']
        keyword_to_test = str(self.input)
        packets = IP(dst=backend_ip,id=RandShort())/TCP(dport=backend_port)/keyword_to_test
        d = self.sr(packets, timeout=timeout)
        d.addCallback(finished)
        return d


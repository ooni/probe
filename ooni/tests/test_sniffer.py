import re
import os

from scapy.all import IP, TCP
from ooni.sniffer import ScapySniffer, pcapdnet_installed, Filter

from twisted.trial.unittest import TestCase


class TestSniffer(TestCase):
    def setUp(self):
        self.filenames = []

    def tearDown(self):
        for filename in self.filenames:
            os.unlink(filename)

    def test_pcapdnet_installed(self):
        assert pcapdnet_installed() is True

    def test_sniffer_http_url(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.original = "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('www.torproject.org/something/fancy')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        self.assertEqual(len(sniffer._conns), 1)
        self.assertEqual(sniffer._conns[0]['src'], '10.0.2.1')
        self.assertEqual(sniffer._conns[0]['dst'], '10.0.2.2')
        self.assertEqual(sniffer._conns[0]['dport'], 80)
        self.assertEqual(sniffer._conns[0]['sport'], 8080)
        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=81)
        packet.payload.payload.original = "GET /something/weird HTTP/1.0\r\n\r\n"
        sniffer.packetReceived(packet)
        self.assertEqual(size, os.stat(pcap_filename).st_size)

    def test_sniffer_http_url_with_http(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('http://www.torproject.org/something/fancy')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        self.assertEqual(len(sniffer._conns), 1)
        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

    def test_sniffer_http_url_root(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "GET / HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('http://www.torproject.org')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "DUMB / HTTP/1.0\r\n\r\n"
        sniffer.packetReceived(packet)
        self.assertEqual(os.stat(pcap_filename).st_size, size)

    def test_sniffer_http_url_ip_dst(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "GET / HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('http://10.0.2.2')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

    def test_sniffer_regex_ip(self):
        filter = Filter()
        self.assertIsNotNone(re.match(filter._ip_regex, '110.0.2.2'))
        self.assertIsNone(re.match(filter._ip_regex, '1.1.1.1.1'))
        self.assertIsNone(re.match(filter._ip_regex, '1111.1.1.1'))

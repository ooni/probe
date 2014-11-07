import re
import os

from scapy.all import IP, TCP, Ether
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

    def test_sniffer_filters(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        sniffer = ScapySniffer(pcap_filename)
        filter1 = Filter()
        sniffer.add_filter(filter1)
        self.assertEqual(len(sniffer.get_filters()), 1)
        self.assertIn(filter1, sniffer.get_filters())

        filter2 = Filter()
        sniffer.add_filter(filter2)
        self.assertEqual(len(sniffer.get_filters()), 2)
        self.assertIn(filter2, sniffer.get_filters())

        sniffer.del_filter(filter1)
        self.assertEqual(len(sniffer.get_filters()), 1)
        self.assertNotIn(filter1, sniffer.get_filters())
        self.assertIn(filter2, sniffer.get_filters())

        sniffer.del_filter(filter2)
        self.assertEqual(len(sniffer.get_filters()), 0)
        self.assertNotIn(filter2, sniffer.get_filters())

    def test_sniffer_tcp_udp_rules(self):
        ffilter = Filter()
        ffilter.add_tcp_rule(dport=666, sport=667)
        rules = ffilter.get_rules()
        self.assertEqual(len(rules), 3)
        self.assertIn('tcp', rules)
        self.assertTrue(rules['tcp'])
        self.assertIn('dport', rules)
        self.assertEqual(666, rules['dport'])
        self.assertIn('sport', rules)
        self.assertEqual(667, rules['sport'])

        ffilter.add_tcp_rule(dport=69, sport=70)
        self.assertEqual(len(rules), 3)
        self.assertIn('tcp', rules)
        self.assertTrue(rules['tcp'])
        self.assertIn('dport', rules)
        self.assertEqual(69, rules['dport'])
        self.assertIn('sport', rules)
        self.assertEqual(70, rules['sport'])

        ffilter.add_udp_rule(dport=69, sport=70)
        self.assertEqual(len(rules), 3)
        self.assertIn('tcp', rules)
        self.assertNotIn('udp', rules)

    def test_sniffer_http_correct(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.payload.original = "Host: torproject.org\r\n" \
                                                  "MORE USEFUL HEADERS\r\n" \
                                                  "GET /something/fancy HTTP/1.0\r\n\r\n"
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

        packet = Ether() / IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.payload.original = "Response with the web page"
        sniffer.packetReceived(packet)
        self.assertEqual(size, os.stat(pcap_filename).st_size)

    def test_sniffer_http_with_www(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.payload.original = "Host: www.torproject.org\r\n" \
                                          "MORE USEFUL HEADERS\r\n" \
                                          "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('www.torproject.org/something/fancy')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        self.assertEqual(len(sniffer._conns), 1)
        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

    def test_sniffer_http_empty_resource(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.payload.original = "Host: torproject.org\r\n" \
                                          "MORE USEFUL HEADERS\r\n" \
                                          "GET / HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('www.torproject.org')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        self.assertEqual(len(sniffer._conns), 1)
        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

    def test_sniffer_http_invalid_resource(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.payload.original = "Host: torproject.org\r\n" \
                                          "MORE USEFUL HEADERS\r\n" \
                                          "GET /something/weird HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('www.torproject.org/something/fancy')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)
        self.assertEqual(len(sniffer._conns), 0)
        size = os.stat(pcap_filename).st_size
        self.assertEqual(size, 0)

    def test_sniffer_http_invalid_host(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.payload.original = "Host: wired.org\r\n" \
                                          "MORE USEFUL HEADERS\r\n" \
                                          "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('www.torproject.org/something/fancy')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)
        self.assertEqual(len(sniffer._conns), 0)
        size = os.stat(pcap_filename).st_size
        self.assertEqual(size, 0)

    def test_sniffer_http_incomplete(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)

        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.payload.original = "Host: torproject.org\r\n" \
                                          "MORE USEFUL HEADERS\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('www.torproject.org/something/fancy')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)
        self.assertEqual(len(sniffer._conns), 0)
        size = os.stat(pcap_filename).st_size
        self.assertEqual(size, 0)

        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.payload.original = "MORE USEFUL HEADERS\r\n" \
                                          "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer.packetReceived(packet)
        self.assertEqual(len(sniffer._conns), 0)
        size = os.stat(pcap_filename).st_size
        self.assertEqual(size, 0)

    def test_sniffer_http_with_http(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = Ether() / IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.payload.original = "Host: torproject.org\r\n" \
                                          "MORE USEFUL HEADERS\r\n" \
                                          "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('http://www.torproject.org/something/fancy')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        self.assertEqual(len(sniffer._conns), 1)
        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

    def test_sniffer_http_ip_dst(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=8080, sport=80)
        sniffer = ScapySniffer(pcap_filename)
        filter = Filter()
        filter.add_http_rule('http://10.0.2.2')
        sniffer.add_filter(filter)
        sniffer.packetReceived(packet)

        self.assertEqual(len(sniffer._conns), 1)
        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

        packet = Ether() / IP(src='10.0.2.1', dst='10.0.2.32') / TCP(dport=8080, sport=80)
        sniffer.packetReceived(packet)
        self.assertEqual(size, os.stat(pcap_filename).st_size)

    def test_sniffer_regex_ip(self):
        filter = Filter()
        self.assertIsNotNone(re.match(filter._ip_regex, '110.0.2.2'))
        self.assertIsNone(re.match(filter._ip_regex, '1.1.1.1.1'))
        self.assertIsNone(re.match(filter._ip_regex, '1111.1.1.1'))

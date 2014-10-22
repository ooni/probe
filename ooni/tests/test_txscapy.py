import os
import re

from mock import MagicMock
from twisted.internet import defer
from twisted.trial import unittest

from scapy.all import IP, TCP

from ooni.utils import txscapy

defer.setDebugging(True)


class TestTxScapy(unittest.TestCase):
    def setUp(self):
        mock_super_socket = MagicMock()
        mock_super_socket.ins.fileno.return_value = 1
        self.scapy_factory = txscapy.ScapyFactory('foo', mock_super_socket)
        self.filenames = []

    def tearDown(self):
        self.scapy_factory.connectionLost(None)
        for filename in self.filenames:
            os.unlink(filename)

    def test_pcapdnet_installed(self):
        assert txscapy.pcapdnet_installed() is True

    def test_send_packet_no_answer(self):
        from scapy.all import IP, TCP

        sender = txscapy.ScapySender()
        self.scapy_factory.registerProtocol(sender)
        packet = IP(dst='8.8.8.8') / TCP(dport=53)
        sender.startSending([packet])
        self.scapy_factory.super_socket.send.assert_called_with(packet)
        assert len(sender.sent_packets) == 1

    @defer.inlineCallbacks
    def test_send_packet_with_answer(self):
        from scapy.all import IP, TCP

        sender = txscapy.ScapySender()
        self.scapy_factory.registerProtocol(sender)

        packet_sent = IP(dst='8.8.8.8', src='127.0.0.1') / TCP(dport=53,
                                                               sport=5300)
        packet_received = IP(dst='127.0.0.1', src='8.8.8.8') / TCP(sport=53,
                                                                   dport=5300)

        d = sender.startSending([packet_sent])
        self.scapy_factory.super_socket.send.assert_called_with(packet_sent)

        sender.packetReceived(packet_received)

        result = yield d
        assert result[0][0][0] == packet_sent
        assert result[0][0][1] == packet_received

    def test_get_addresses(self):
        addresses = txscapy.getAddresses()
        assert isinstance(addresses, list)

    def test_sniffer_http_url(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=80, sport=8080)
        packet.payload.payload.original = "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer = txscapy.ScapySniffer(pcap_filename)
        sniffer.filters.append({'http_url': 'www.torproject.org/something/fancy'})
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

        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        sniffer.packetReceived(packet)
        self.assertGreater(os.stat(pcap_filename).st_size, size)

    def test_sniffer_http_url_with_http(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "GET /something/fancy HTTP/1.0\r\n\r\n"
        sniffer = txscapy.ScapySniffer(pcap_filename)
        sniffer.filters.append({'http_url': 'http://www.torproject.org/something/fancy'})
        sniffer.packetReceived(packet)

        self.assertEqual(len(sniffer._conns), 1)
        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

    def test_sniffer_http_url_root(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "GET / HTTP/1.0\r\n\r\n"
        sniffer = txscapy.ScapySniffer(pcap_filename)
        sniffer.filters.append({'http_url': 'www.torproject.org'})
        sniffer.packetReceived(packet)

        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

        packet = IP() / TCP()
        packet = IP(src='10.0.2.2', dst='10.0.2.1') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "DUMB / HTTP/1.0\r\n\r\n"
        sniffer.packetReceived(packet)
        self.assertEqual(os.stat(pcap_filename).st_size, size)

    def test_sniffer_http_url_ip_dst(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        packet = IP(src='10.0.2.1', dst='10.0.2.2') / TCP(dport=8080, sport=80)
        packet.payload.payload.original = "GET / HTTP/1.0\r\n\r\n"
        sniffer = txscapy.ScapySniffer(pcap_filename)
        sniffer.filters.append({'http_url': 'http://10.0.2.2'})
        sniffer.packetReceived(packet)

        size = os.stat(pcap_filename).st_size
        self.assertGreater(size, 0)

    def test_sniffer_regex_ip(self):
        pcap_filename = 'sniffer.pcap'
        self.filenames.append(pcap_filename)
        sniffer = txscapy.ScapySniffer(pcap_filename)
        self.assertIsNotNone(re.match(sniffer.ip_regex, '110.0.2.2'))
        self.assertIsNone(re.match(sniffer.ip_regex, '1.1.1.1.1'))
        self.assertIsNone(re.match(sniffer.ip_regex, '1111.1.1.1'))

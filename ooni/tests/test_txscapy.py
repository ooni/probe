import os

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

    def test_send_packet_no_answer(self):
        sender = txscapy.ScapySender()
        self.scapy_factory.registerProtocol(sender)
        packet = IP(dst='8.8.8.8') / TCP(dport=53)
        sender.startSending([packet])
        self.scapy_factory.super_socket.send.assert_called_with(packet)
        assert len(sender.sent_packets) == 1

    @defer.inlineCallbacks
    def test_send_packet_with_answer(self):
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
import sys
import yaml

from twisted.internet import protocol, defer
from twisted.internet.error import ConnectionDone

from scapy.all import IP, Raw, rdpcap

from ooni.utils import log

def read_pcap(filename):
    """
    @param filename: Filesystem path to the pcap.

    Returns:
      [{"sender": "client", "data": "\x17\x52\x15"}, {"sender": "server", "data": "\x17\x15\x13"}]
    """
    packets = rdpcap(filename)

    checking_first_packet = True
    client_ip_addr = None
    server_ip_addr = None

    ssl_packets = []
    messages = []

    """
    pcap assumptions:

    pcap only contains packets exchanged between a Tor client and a Tor
    server.  (This assumption makes sure that there are only two IP addresses
    in the pcap file)

    The first packet of the pcap is sent from the client to the server. (This
    assumption is used to get the IP address of the client.)

    All captured packets are TLS packets: that is TCP session
    establishment/teardown packets should be filtered out (no SYN/SYN+ACK)
    """

    """
    Minimally validate the pcap and also find out what's the client
    and server IP addresses.
    """
    for packet in packets:
        if checking_first_packet:
            client_ip_addr = packet[IP].src
            checking_first_packet = False
        else:
            if packet[IP].src != client_ip_addr:
                server_ip_addr = packet[IP].src

        try:
            if (packet[Raw]):
                ssl_packets.append(packet)
        except IndexError:
            pass

    """Form our list."""
    for packet in ssl_packets:
        if packet[IP].src == client_ip_addr:
            messages.append({"sender": "client", "data": str(packet[Raw])})
        elif packet[IP].src == server_ip_addr:
            messages.append({"sender": "server", "data": str(packet[Raw])})
        else:
            raise("Detected third IP address! pcap is corrupted.")

    return messages

def read_yaml(filename):
    f = open(filename)
    obj = yaml.load(f)
    f.close()
    return obj

class NoInputSpecified(Exception):
    pass

class Daphn3Protocol(protocol.Protocol):
    def __init__(self, yaml_file=None, pcap_file=None, role="client"):
        if yaml_file:
            self.packets = read_yaml(yaml_file)
        elif pcap_file:
            self.packets = read_pcap(pcap_file)
        else:
            raise NoInputSpecified

        self.role = role
        # We use this index to keep track of where we are in the state machine
        self.current_step = 0

        # 0 indicates we are waiting to receive data, while 1 indicates we are
        # sending data 
        self.current_state = 0
        self.current_data_received = 0

    def dataReceived(self, data):
        self.current_data_received += len(data)
        expected_data_in_this_state = len(self.packets[self.current_step][self.role])
        if len(self.current_data_received)



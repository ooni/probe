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
      [{"client": "\x17\x52\x15"}, {"server": "\x17\x15\x13"}]
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
            messages.append({"client": str(packet[Raw])})
        elif packet[IP].src == server_ip_addr:
            messages.append({"server": str(packet[Raw])})
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

class StateError(Exception):
    pass

def daphn3MutateString(string, i):
    """
    Takes a string and mutates the ith bytes of it.
    """
    mutated = ""
    for y in range(len(string)):
        if y == i:
            mutated += chr(ord(string[i]) + 1)
        else:
            mutated += string[i]
    return mutated

def daphn3Mutate(steps, step_idx, mutation_idx):
    """
    Take a set of steps and a step index and mutates the step of that
    index at the mutation_idx'th byte.
    """
    mutated_steps = []
    for idx, step in enumerate(steps):
        if idx == step_idx:
            step_string = step.values()[0]
            step_key = step.keys()[0]
            mutated_string = daphn3MutateString(step_string, 
                    mutation_idx)
            mutated_steps.append({step_key: mutated_string})
        else:
            mutated_steps.append(step)
    return mutated_steps

class Daphn3Protocol(protocol.Protocol):
    def __init__(self, steps=None, 
            yaml_file=None, pcap_file=None, 
            role="client"):
        if yaml_file:
            self.steps = read_yaml(yaml_file)
        elif pcap_file:
            self.steps = read_pcap(pcap_file)
        elif steps:
            self.steps = steps
        else:
            raise NoInputSpecified

        # XXX remove me
        #self.steps = [{'client': 'antani'}, {'server': 'sblinda'}]
        self.role = role
        # We use this index to keep track of where we are in the state machine
        self.current_step = 0

        # 0 indicates we are waiting to receive data, while 1 indicates we are
        # sending data
        self.current_state = 0
        self.current_data_received = 0

    def sendMutation(self):
        self.debug("Sending mutation")
        current_step_role = self.steps[self.current_step].keys()[0]
        current_step_data = self.steps[self.current_step].values()[0]
        if current_step_role == self.role:
            print "In a state to do shit %s" % current_step_data
            self.transport.write(current_step_data)
            self.nextState()
        else:
            print "Not in a state to do anything"

    def connectionMade(self):
        print "Got connection"
        self.sendMutation()

    def debug(self, msg):
        print "Current step %s" % self.current_step
        print "Current data received %s" % self.current_data_received
        print "Current role %s" % self.role
        print "Current steps %s" % self.steps
        print "Current state %s" % self.current_state

    def nextState(self):
        print "Moving on to next state"
        self.current_data_received = 0
        self.current_step += 1
        if self.current_step >= len(self.steps):
            print "Going to loose this connection"
            self.transport.loseConnection()
            return
        self.sendMutation()

    def dataReceived(self, data):
        current_step_role = self.steps[self.current_step].keys()[0]
        log.debug("Current step role %s" % current_step_role)
        if current_step_role == self.role:
            log.debug("Got a state error!")
            raise StateError("I should not have gotten data, while I did, \
                    perhaps there is a wrong state machine?")

        self.current_data_received += len(data)
        expected_data_in_this_state = len(self.steps[self.current_step].values()[0])

        log.debug("Current data received %s" %  self.current_data_received)
        if self.current_data_received >= expected_data_in_this_state:
            self.nextState()

    def connectionLost(self, reason):
        self.debug("Lost the connection")
        print reason


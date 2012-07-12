from ooni.utils import log

import sys
from scapy.all import * # XXX recommended way of importing scapy?
import yaml

def get_b0wser_dictionary_from_pcap(filename):
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
    server. (This assumption makes sure that there are only two IP
    addresses in the pcap file)

    The first packet of the pcap is sent from the client to the server.
    (This assumption is used to get the IP address of the client.)

    All captured packets are TLS packets: that is TCP session
    establishment/teardown packets should be filtered out (no SYN/SYN+ACK)
    """

    """Minimally validate the pcap and also find out what's the client
    and server IP addresses."""
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

    return yaml.dump(messages)

class Mutator:
    idx = 0
    step = 0

    waiting = False
    waiting_step = 0

    def __init__(self, steps):
        """
        @param steps: array of dicts containing as keys data and wait. Data is
                      the content of the ith packet to be sent and wait is how
                      much we should wait before mutating the packet of the
                      next step.
        """
        self.steps = steps

    def _mutate(self, data, idx):
        """
        Mutate the idx bytes by increasing it's value by one

        @param data: the data to be mutated.

        @param idx: what byte should be mutated.
        """
        print "idx: %s, data: %s" % (idx, data)
        ret = data[:idx]
        ret += chr(ord(data[idx]) + 1)
        ret += data[idx+1:]
        return ret

    def state(self):
        """
        Return the current mutation state. As in what bytes are being mutated.

        Returns a dict containg the packet index and the step number.
        """
        return {'idx': self.idx, 'step': self.step}

    def next_mutation(self):
        """
        Increases by one the mutation state.

        ex. (* is the mutation state, i.e. the byte to be mutated)
        before [___*] [____]
               step1   step2
        after  [____] [*___]

        Should be called every time you need to proceed onto the next mutation.
        It changes the internal state of the mutator to that of the next
        mutatation.

        returns True if another mutation is available.
        returns False if all the possible mutations have been done.
        """
        if self.step > len(self.steps):
            self.waiting = True
            return False

        self.idx += 1
        current_idx = self.idx
        current_step = self.step
        current_data = self.steps[current_step]['data']
        data_to_receive = self.steps[current_step]['wait']

        if self.waiting and self.waiting_step == data_to_receive:
            log.debug("I am no longer waiting.")
            self.waiting = False
            self.waiting_step = 0
            self.idx = 0

        elif self.waiting:
            log.debug("Waiting some more.")
            self.waiting_step += 1

        elif current_idx >= len(current_data):
            log.debug("Entering waiting mode.")
            self.step += 1
            self.idx = 0
            self.waiting = True
        log.debug("current index %s" % current_idx)
        log.debug("current data %s" % len(current_data))
        return True

    def get_mutation(self, step):
        """
        Returns the current packet to be sent to the wire.
        If no mutation is necessary it will return the plain data.
        Should be called when you are interested in obtaining the data to be
        sent for the selected state.

        @param step: the current step you want the mutation for

        returns the mutated packet for the specified step.
        """
        if step != self.step or self.waiting:
            log.debug("I am not going to do anything :)")
            return self.steps[step]['data']

        data = self.steps[step]['data']
        print "Mutating %s with idx %s" % (data, self.idx)
        return self._mutate(data, self.idx)


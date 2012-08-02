import sys
import yaml

from twisted.internet import protocol, defer
from twisted.internet.error import ConnectionDone

from scapy.all import *

from ooni.utils import log
from ooni.plugoo import reports

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

    pcap only contains packets exchanged between a Tor client and a Tor server.
    (This assumption makes sure that there are only two IP addresses in the
    pcap file)

    The first packet of the pcap is sent from the client to the server. (This
    assumption is used to get the IP address of the client.)

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

    return messages

def read_yaml(filename):
    f = open(filename)
    obj = yaml.load(f)
    f.close()
    return obj

class Mutator:
    idx = 0
    step = 0

    waiting = False
    waiting_step = 0

    def __init__(self, steps):
        """
        @param steps: array of dicts for the steps that must be gone over by
                      the mutator. Looks like this:
                      [{"sender": "client", "data": "\xde\xad\xbe\xef"},
                       {"sender": "server", "data": "\xde\xad\xbe\xef"}]
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
        print "[Mutator.state()] Giving out my internal state."
        current_state =  {'idx': self.idx, 'step': self.step}
        return current_state

    def next(self):
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
        if (self.step) == len(self.steps):
            # Hack to stop once we have gone through all the steps
            print "[Mutator.next()] I believe I have gone over all steps"
            print "                          Stopping!"
            self.waiting = True
            return False

        self.idx += 1
        current_idx = self.idx
        current_step = self.step
        current_data = self.steps[current_step]['data']

        if 0:
            print "current_step: %s" % current_step
            print "current_idx: %s" % current_idx
            print "current_data: %s" % current_data
            print "steps: %s" % len(self.steps)
            print "waiting_step: %s" % self.waiting_step

        data_to_receive = len(self.steps[current_step]['data'])

        if self.waiting and self.waiting_step == data_to_receive:
            print "[Mutator.next()] I am no longer waiting"
            log.debug("I am no longer waiting.")
            self.waiting = False
            self.waiting_step = 0
            self.idx = 0

        elif self.waiting:
            print "[Mutator.next()] Waiting some more."
            log.debug("Waiting some more.")
            self.waiting_step += 1

        elif current_idx >= len(current_data):
            print "[Mutator.next()] Entering waiting mode."
            log.debug("Entering waiting mode.")
            self.step += 1
            self.idx = 0
            self.waiting = True

        log.debug("current index %s" % current_idx)
        log.debug("current data %s" % len(current_data))
        return True

    def get(self, step):
        """
        Returns the current packet to be sent to the wire.
        If no mutation is necessary it will return the plain data.
        Should be called when you are interested in obtaining the data to be
        sent for the selected state.

        @param step: the current step you want the mutation for

        returns the mutated packet for the specified step.
        """
        if step != self.step or self.waiting:
            log.debug("[Mutator.get()] I am not going to do anything :)")
            return self.steps[step]['data']

        data = self.steps[step]['data']
        #print "Mutating %s with idx %s" % (data, self.idx)
        return self._mutate(data, self.idx)

class Daphn3Protocol(protocol.Protocol):
    """
    This implements the Daphn3 protocol for the server side.
    It gets instanced once for every client that connects to the oonib.
    For every instance of protocol there is only 1 mutation.
    Once the last step is reached the connection is closed on the serverside.
    """
    steps = []
    mutator = None

    role = 'client'
    state = 0
    total_states = len(steps) - 1
    received_data = 0
    to_receive_data = 0
    report = reports.Report('daphn3', 'daphn3.yamlooni')

    test = None

    def next_state(self):
        """
        This is called once I have completed one step of the protocol and need
        to proceed to the next step.
        """
        if not self.mutator:
            print "[Daphn3Protocol.next_state] No mutator. There is no point to stay on this earth."
            self.transport.loseConnection()
            return

        if self.role is self.steps[self.state]['sender']:
            print "[Daphn3Protocol.next_state] I am a sender"
            data = self.mutator.get(self.state)
            self.transport.write(data)
            self.to_receive_data = 0

        else:
            print "[Daphn3Protocol.next_state] I am a receiver"
            self.to_receive_data = len(self.steps[self.state]['data'])

        self.state += 1
        self.received_data = 0

    def dataReceived(self, data):
        """
        This is called every time some data is received. I transition to the
        next step once the amount of data that I expect to receive is received.

        @param data: the data that has been sent by the client.
        """
        if not self.mutator:
            print "I don't have a mutator. My life means nothing."
            self.transport.loseConnection()
            return

        if len(self.steps) == self.state:
            self.transport.loseConnection()
            return

        self.received_data += len(data)
        if self.received_data >= self.to_receive_data:
            print "Moving to next state %s" % self.state
            self.next_state()

    def censorship_detected(self, report):
        """
        I have detected the possible presence of censorship we need to write a
        report on it.

        @param report: a dict containing the report to be written. Must contain
                       the keys 'reason', 'proto_state' and 'mutator_state'.
                       The reason is the reason for which the connection was
                       closed. The proto_state is the current state of the
                       protocol instance and mutator_state is what was being
                       mutated.
        """
        print "The connection was closed because of %s" % report['reason']
        print "State %s, Mutator %s" % (report['proto_state'],
                                        report['mutator_state'])
        if self.test:
            self.test.result['censored'] = True
            self.test.result['state'] = report
        self.mutator.next()

    def connectionLost(self, reason):
        """
        The connection was closed. This may be because of a legittimate reason
        or it may be because of a censorship event.
        """
        if not self.mutator:
            print "Terminated because of little interest in life."
            return
        report = {'reason': reason, 'proto_state': self.state,
                'trigger': None, 'mutator_state': self.mutator.state()}

        if self.state < self.total_states:
            report['trigger'] = 'did not finish state walk'
            self.censorship_detected(report)

        else:
            print "I have reached the end of the state machine"
            print "Censorship fingerprint bruteforced!"
            if self.test:
                print "In the test thing"
                self.test.result['censored'] = False
                self.test.result['state'] = report
                self.test.result['state_walk_finished'] = True
                self.test.report(self.test.result)
            return

        if reason.check(ConnectionDone):
            print "Connection closed cleanly"
        else:
            report['trigger'] = 'unclean connection closure'
            self.censorship_detected(report)



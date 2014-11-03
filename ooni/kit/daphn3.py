import yaml

from twisted.internet import protocol, defer

from ooni.utils import log

def read_pcap(filename):
    """
    @param filename: Filesystem path to the pcap.

    Returns:
      [{"client": "\x17\x52\x15"}, {"server": "\x17\x15\x13"}]
    """
    from scapy.all import IP, Raw, rdpcap

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
    obj = yaml.safe_load(f)
    f.close()
    return obj

class NoInputSpecified(Exception):
    pass

class StepError(Exception):
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
            mutated += string[y]
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
    steps = None
    role = "client"
    report = None
    # We use this index to keep track of where we are in the state machine
    current_step = 0
    current_data_received = 0

    # We use this to keep track of the mutated steps
    mutated_steps = None
    d = defer.Deferred()

    def _current_step_role(self):
        return self.steps[self.current_step].keys()[0]

    def _current_step_data(self):
        step_idx, mutation_idx = self.factory.mutation
        log.debug("Mutating %s %s" % (step_idx, mutation_idx))
        mutated_step = daphn3Mutate(self.steps, 
                step_idx, mutation_idx)
        log.debug("Mutated packet into %s" % mutated_step)
        return mutated_step[self.current_step].values()[0]

    def sendPayload(self):
        self.debug("Sending payload")
        current_step_role = self._current_step_role()
        current_step_data = self._current_step_data()
        if current_step_role == self.role:
            print "In a state to do shit %s" % current_step_data
            self.transport.write(current_step_data)
            self.nextStep()
        else:
            print "Not in a state to do anything"

    def connectionMade(self):
        print "Got connection"

    def debug(self, msg):
        log.debug("Current step %s" % self.current_step)
        log.debug("Current data received %s" % self.current_data_received)
        log.debug("Current role %s" % self.role)
        log.debug("Current steps %s" % self.steps)
        log.debug("Current step data %s" % self._current_step_data())

    def nextStep(self):
        """
        XXX this method is overwritten individually by client and server transport.
        There is probably a smarter way to do this and refactor the common
        code into one place, but for the moment like this is good.
        """
        pass

    def dataReceived(self, data):
        current_step_role = self.steps[self.current_step].keys()[0]
        log.debug("Current step role %s" % current_step_role)
        if current_step_role == self.role:
            log.debug("Got a state error!")
            raise StepError("I should not have gotten data, while I did, \
                    perhaps there is something wrong with the state machine?")

        self.current_data_received += len(data)
        expected_data_in_this_state = len(self.steps[self.current_step].values()[0])

        log.debug("Current data received %s" %  self.current_data_received)
        if self.current_data_received >= expected_data_in_this_state:
            self.nextStep()

    def nextMutation(self):
        log.debug("Moving onto next mutation")
        # [step_idx, mutation_idx]
        c_step_idx, c_mutation_idx = self.factory.mutation
        log.debug("[%s]: c_step_idx: %s | c_mutation_idx: %s" % (self.role,
            c_step_idx, c_mutation_idx))

        if c_step_idx >= (len(self.steps) - 1):
            log.err("No censorship fingerprint bisected.")
            log.err("Givinig up.")
            self.transport.loseConnection()
            return

        # This means we have mutated all bytes in the step
        # we should proceed to mutating the next step.
        log.debug("steps: %s | %s" % (self.steps, self.steps[c_step_idx]))
        if c_mutation_idx >= (len(self.steps[c_step_idx].values()[0]) - 1):
            log.debug("Finished mutating step")
            # increase step
            self.factory.mutation[0] += 1
            # reset mutation idx
            self.factory.mutation[1] = 0
        else:
            log.debug("Mutating next byte in step")
            # increase mutation index
            self.factory.mutation[1] += 1

    def connectionLost(self, reason):
        self.debug("--- Lost the connection ---")
        self.nextMutation()


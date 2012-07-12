from ooni.utils import log

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

class B0wserProtocol(protocol.Protocol):
    """
    This implements the B0wser protocol for the server side.
    It gets instanced once for every client that connects to the oonib.
    For every instance of protocol there is only 1 mutation.
    Once the last step is reached the connection is closed on the serverside.
    """
    steps = [{'data': "STEP1", 'wait': 4},
             {'data': "STEP2", 'wait': 4},
             {'data': "STEP3", 'wait': 4}]
    mutator = None

    state = 0
    total_states = len(steps) - 1
    received_data = 0
    report = reports.Report('b0wser', 'b0wser.yamlooni')

    def next_state(self):
        """
        This is called once I have completed one step of the protocol and need
        to proceed to the next step.
        """
        data = self.mutator.get_mutation(self.state)
        self.transport.write(data)
        self.state += 1
        self.received_data = 0

    def dataReceived(self, data):
        """
        This is called every time some data is received. I transition to the
        next step once the amount of data that I expect to receive is received.

        @param data: the data that has been sent by the client.
        """
        if len(self.steps) <= self.state:
            print "I have reached the end of the state machine"
            print "Censorship fingerprint bruteforced!"
            report = {'mutator_state': self.mutator.state()}
            self.report(report)
            self.transport.loseConnection()
            return
        self.received_data += len(data)
        if self.received_data >= self.steps[self.state]['wait']:
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
        self.mutator.next_mutation()



    def connectionLost(self, reason):
        """
        The connection was closed. This may be because of a legittimate reason
        or it may be because of a censorship event.
        """
        report = {'reason': reason, 'proto_state': self.state,
                'mutator_state': self.mutator.state(), 'trigger': None}

        if self.state < self.total_states:
            report['trigger'] = 'did not finish state walk'
            self.censorship_detected(report)

        if reason.check(ConnectionDone):
            print "Connection closed cleanly"
        else:
            report['trigger'] = 'unclean connection closure'
            self.censorship_detected(report)



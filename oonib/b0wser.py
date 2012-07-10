from twisted.internet import protocol

class Mutator:
    idx = 0
    step = 0

    waiting = False
    waiting_step = 0

    def __init__(self, steps):
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
            print "I am no longer waiting..."
            self.waiting = False
            self.waiting_step = 0
            self.idx = 0

        elif self.waiting:
            print "Waiting some more..."
            self.waiting_step += 1

        elif current_idx >= len(current_data):
            print "Entering waiting mode..."
            self.step += 1
            self.idx = 0
            self.waiting = True
        print "current index %s current data %s" % (current_idx, len(current_data))
        return True

    def get_mutation(self, state):
        """
        Returns the current packet to be sent to the wire.
        If no mutation is necessary it will return the plain data.
        Should be called when you are interested in obtaining the data to be
        sent for the selected state.

        @param step: the current step you want the mutation for

        returns the mutated packet for the specified step.
        """
        if step != self.step or self.waiting:
            print "I am not going to do anything :)"
            return self.steps[step]['data']

        data = self.steps[step]['data']
        print "Mutating %s with idx %s" % (data, self.idx)
        return self._mutate(data, self.idx)

class B0wserProtocol(protocol.Protocol):
    steps = [{'data': "STEP1", 'wait': 4},
             {'data': "STEP2", 'wait': 4},
             {'data': "STEP3", 'wait': 4}]

    mutator = None
    state = 0
    received_data = 0

    def next_state(self):
        data = self.mutator.get_mutation(self.state)
        self.transport.write(data)
        self.state += 1
        self.received_data = 0

    def dataReceived(self, data):
        if len(self.steps) <= self.state:
            self.transport.loseConnection()
            return
        self.received_data += len(data)
        if self.received_data >= self.steps[self.state]['wait']:
            print "Moving to next state %s" % self.state
            self.next_state()

class B0wserServer(protocol.ServerFactory):
    protocol = B0wserProtocol
    mutations = {}
    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self

        if addr.host not in self.mutations:
            self.mutations[addr.host] = Mutator(p.steps)
        else:
            print "Moving on to next mutation"
            self.mutations[addr.host].next_mutation()
        p.mutator = self.mutations[addr.host]
        return p


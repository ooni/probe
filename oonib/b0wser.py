from twisted.internet import protocol

class Mutator:
    idx = 0
    step = 0
    state = 0
    waiting = False
    waiting_step = 0

    def __init__(self, steps):
        self.steps = steps

    def next_mutation(self):
        """
        Increases by one the mutation state.

        ex. (* is the mutation state, i.e. the byte to be mutated)
        before [___*] [____]
               step1   step2
        after  [____] [*___]
        """
        current_idx = self.idx + 1
        current_step = self.step
        current_data = self.steps[c_step]['data']
        data_to_receive = self.steps[c_step]]['recv']

        if self.waiting and self.waiting_step == data_to_receive:
            self.waiting = False
            self.waiting_step = 0

        elif self.waiting:
            self.waiting_step += 1

        elif current_idx > len(current_data):
            self.step += 1
            self.idx = 0
            self.waiting = True

    @classmethod
    def mutate(data, idx):
        """
        Mutate the idx bytes by increasing it's value by one

        @param data: the data to be mutated.

        @param idx: what byte should be mutated.
        """
        ret = data[:idx-1]
        ret += chr(ord(data[idx]) + 1)
        ret += data[idx:]
        return ret

    def get_mutation(self):
        """
        returns the current packet to be sent to the wire.
        If no mutation is necessary it will return the plain data.
        """
        self.next_mutation()
        if self.state != self.step or self.waiting:
            return self.steps[self.state]

        data = self.steps[self.state]
        return self.mutate(data, self.idx)

    def get_data(self, i):
        """
        XXX remove this shit.
        """
        j = 0
        pkt_size = len(self.steps[j]['data'])
        while i > pkt_size:
            j += 1
            pkt_size += len(self.steps[j])
        # I am not in a state to send mutations
        if j != self.state:
            return self.steps[j]['data']

        rel_idx = i % (pkt_size - len(self.steps[j-1]))
        data = self.steps[j]
        data[rel_idx] = chr(ord(data[rel_idx]) + 1)
        return data

class B0wserProtocol(protocol.Protocol):
    steps = [{'data': "STEP1", 'recv': 20},
             {'data': "STEP2", 'recv': 20},
             {'data': "STEP3", 'recv': 20}]

    mutator = None
    state = 0
    received_data = 0

    def next_state(self):
        data = self.mutator.get_mutation()
        self.transport.write(data)
        self.mutator.state += 1
        self.received_data = 0

    def dataReceived(self, data):
        if len(self.steps) <= self.state:
            self.transport.loseConnection()
            return
        self.received_data += len(data)
        if self.received_data >= self.steps[self.state]['recv']:
            print self.received_data
            self.next_state()

class B0wserServer(protocol.ServerFactory):
    protocol = B0wserProtocol
    mutations = {}
    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self

        if addr.host not in self.mutations:
            self.mutations[addr.host] = Mutation(p.steps)
        p.mutator = self.mutations[addr.host]
        return p

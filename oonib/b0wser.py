from twisted.internet import protocol
from twisted.internet.error import ConnectionDone

from ooni.plugoo import reports
from ooni.protocols.b0wser import Mutator

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
        print "I may have matched the censorship fingerprint"
        print "State %s, Mutator %s" % (report['proto_state'],
                                        report['mutator_state'])
        self.report(report)


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

class B0wserServer(protocol.ServerFactory):
    """
    This is the main class that deals with the b0wser server side component.
    We keep track of global state of every client here.
    Every client is identified by their IP address and the state of mutation is
    stored by using their IP address as a key. This may lead to some bugs if
    two different clients are sharing the same IP, but hopefully the
    probability of such thing is not that likely.
    """
    protocol = B0wserProtocol
    mutations = {}
    def buildProtocol(self, addr):
        p = self.protocol()
        p.factory = self

        if addr.host not in self.mutations:
            self.mutations[addr.host] = Mutator(p.steps)
        else:
            print "Moving on to next mutation"
            if not self.mutations[addr.host].next_mutation():
                self.mutations.pop(addr.host)
        p.mutator = self.mutations[addr.host]
        return p


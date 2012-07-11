from twisted.internet import protocol
from twisted.internet.error import ConnectionDone

from ooni.plugoo import reports
from ooni.protocols.b0wser import Mutator

class B0wserProtocol(protocol.Protocol):
    steps = [{'data': "STEP1", 'wait': 4},
             {'data': "STEP2", 'wait': 4},
             {'data': "STEP3", 'wait': 4}]
    mutator = None

    state = 0
    total_states = len(steps) - 1
    received_data = 0
    report = reports.Report('b0wser', 'b0wser.yamlooni')

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

    def censorship_detected(self, report):
        print "The connection was closed because of %s" % report['reason']
        print "I may have matched the censorship fingerprint"
        print "State %s, Mutator %s" % (report['proto_state'],
                                        report['mutator_state'])
        self.report(report)


    def connectionLost(self, reason):
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


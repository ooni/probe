from twisted.internet import protocol
from twisted.internet.error import ConnectionDone

from ooni.plugoo import reports
from ooni.protocols.b0wser import Mutator, B0wserProtocol

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


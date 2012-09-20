#
# circuit.py
# ----------
# Utilities for working with Tor circuits.
#
# This code is largely taken from attach_streams_by_country.py in the txtorcon
# documentation, and as such any and all credit should go to meejah. Minor
# adjustments have been made to use OONI's logging system, and to build custom
# circuits without actually attaching streams.
#
# :author: Meejah, Isis Lovecruft
# :license: see included LICENSE file
# :version: 0.1.0-alpha
#

import random

from ooni.lib.txtorcon import CircuitListenerMixin, IStreamAttacher
from ooni.lib.txtorcon import TorInfo
from ooni.utils        import log
from zope.interface    import implements


class CustomCircuit(CircuitListenerMixin):
    implements(IStreamAttacher)

    def __init__(self, state, relays=None):
        self.state = state
        self.waiting_circuits = []
        self.relays = relays

    def waiting_on(self, circuit):
        for (circid, d) in self.waiting_circuits:
            if circuit.id == circid:
                return True
        return False

    def circuit_extend(self, circuit, router):
        "ICircuitListener"
        if circuit.purpose != 'GENERAL':
            return
        if self.waiting_on(circuit):
            log.msg("Circuit %d (%s)" % (circuit.id, router.id_hex))

    def circuit_built(self, circuit):
        "ICircuitListener"
        if circuit.purpose != 'GENERAL':
            return
        log.msg("Circuit %s built ..." % circuit.id)
        log.msg("Full path of %s: %s" % (circuit.id, circuit.path))
        for (circid, d) in self.waiting_circuits:
            if circid == circuit.id:
                self.waiting_circuits.remove((circid, d))
                d.callback(circuit)

    def circuit_failed(self, circuit, reason):
        if self.waiting_on(circuit):
            log.msg("Circuit %s failed for reason %s" 
                    % (circuit.id, reason))
            circid, d = None, None
            for c in self.waiting_circuits:
                if c[0] == circuit.id:
                    circid, d = c
            if d is None:
                raise Exception("Expected to find circuit.")

            self.waiting_circuits.remove((circid, d))
            log.msg("Trying to build a circuit for %s" % circid)
            self.request_circuit_build(d)

    def check_circuit_route(self, circuit, router):
        if router in circuit.path:
            #router.update() ## XXX can i use without args? no.
            TorInfo.dump(self)

    def request_circuit_build(self, deferred, path=None):
        if path is None:
            if self.state.relays_remaining() > 0:
                first, middle,last = (self.state.relays.pop()
                                      for i in range(3))
            else:
                first = random.choice(self.state.entry_guards.values())
                middle, last = (random.choice(self.state.routers.values())
                                for i in range(2))
            path = [first, middle, last]
        else:
            assert type(path) is list, "Circuit path must be a list of routers!"
            assert len(path) >= 3, "Circuits must be at least three hops!"

        log.msg("Requesting a circuit: %s" 
                % '->'.join(map(lambda node: node, path)))

        class AppendWaiting:
            def __init__(self, attacher, deferred):
                self.attacher = attacher
                self.d        = deferred
            def __call__(self, circ):
                """
                Return from build_circuit is a Circuit, however,
                we want to wait until it is built before we can
                issue an attach on it and callback to the Deferred
                we issue here.
                """
                log.msg("Circuit %s is in progress ..." % circ.id)
                self.attacher.waiting_circuits.append((circ.id, self.d))

        return self.state.build_circuit(path).addCallback(
            AppendWaiting(self, deferred)).addErrback(
            log.err)

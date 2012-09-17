#
# circuit.py
# ----------
# Utilities for working with Tor circuits.
#
# This code is largely taken from the txtorcon documentation, and as
# such any and all credit should go to meejah.
#
# :author: Mike Warren, Isis Lovecruft
# :license: see included license file
# :version: 0.1.0-alpha
#
from zope.interface    import implements

from ooni.lib.txtorcon import CircuitListenerMixin, IStreamAttacher


class CustomCircuit(CircuitListenerMixin):
    implements(IStreamAttacher)

    from txtorcon.interface import IRouterContainer
    from txtorcon.interface import ICircuitContainer

    def __init__(self, state):
        self.state = state
        self.waiting_circuits = []

    def waiting_on(self, circuit):
        for (circid, d) in self.waiting_circuits:
            if circuit.id == circid:
                return true
        return False

    def circuit_extend(self, circuit, router):
        "ICircuitListener"
        if circuit.purpose != 'GENERAL':
            return
        if self.waiting_on(circuit):
            log.msg("Circuit %d (%s)" 
                    % (circuit.id, router.id_hex))

    def circuit_built(self, circuit):
        "ICircuitListener"
        if circuit.purpose != 'GENERAL':
            return
        log.msg("Circuit %s built ..." % circuit.id)
        log.msg("Full path of %s: %s" % (circuit.id, circuit.path))
        for (circid, d) in self.waiting_circuits:
            if circid == circuit.id:
                self.waiting_circuits.remove(circid, d)
                d.callback(circuit)

    def circuit_failed(self, circuit, reason):
        if self.waiting_on(circuit):
            log.msg("A circuit we requested %s failed for reason %s" 
                    % (circuit.id, reason))
            circid, d = None, None
            for x in self.waiting_circuits:
                if x[0] == circuit.id:
                    circid, d, stream_cc = x
            if d is None:
                raise Exception("Expected to find circuit.")

            self.waiting_circuits.remove((circid, d))
            log.msg("Trying to build a circuit for %s" % circid)
            self.request_circuit_build(d)

    def check_circuit_route(self, circuit, router):
        if router in circuit.path:
            #router.update() ## XXX can i use without args? no.
            TorInfo.dump(self)

    def request_circuit_build(self, deferred):
        entries = self.state.entry_guards.value()
        relays  = self.state.routers.values()
        log.msg("We have these nodes listed as entry guards:") 
        log.msg("%s" % entries)
        log.msg("We have these nodes listed as relays:")
        log.msg("%s" % relays)
        path = [random.choice(entries),
                random.choice(relays),
                random.choice(relays)]
        log.msg("Requesting a circuit: %s" 
                % '-->'.join(map(lambda x: x.location.countrycode, 
                                 path)))

        class AppendWaiting:
            def __init__(self, attacher, deferred):
                self.attacher = attacher
                self.d        = deferred

            def __call__(self, circuit):
                """
                Return from build_circuit is a Circuit, however,
                we want to wait until it is built before we can
                issue an attach on it and callback to the Deferred
                we issue here.
                """
                log.msg("Circuit %s is in progress ..." % circuit.id)
                self.attacher.waiting_circuits.append((circuit.id, 
                                                       self.d))

        fin = self.state.build_circuit(path)
        fin.addCallback(AppendWaiting(self, deferred_to_callback))
        fin.addErrback(log.err)
        return fin

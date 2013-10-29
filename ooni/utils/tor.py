from twisted.internet import protocol, defer, reactor, interfaces
from twisted.internet.endpoints import TCP4ClientEndpoint, _WrappingFactory
from txsocksx.client import SOCKS5ClientFactory
from txtorcon import CircuitListenerMixin, IStreamAttacher, StreamListenerMixin
from zope.interface import implementer

from ooni.utils import log
from ooni.settings import config
import random

@implementer(interfaces.IStreamClientEndpoint)
class TorCircuitContextFactory(object):
    def __init__(self, torState, streamAttacher):
        """
        @param torState: An instance of L{txtorcon.torstate.TorState}
        @param streamAttacher: An instance of L{txtorcon.IStreamAttacher}
        """
        self.state = torState
        self.streamAttacher = streamAttacher

@implementer(interfaces.IStreamClientEndpoint)
class OnionRoutedTCPClientEndpoint(object):
    def __init__(self, reactor, host, port, torCircuitContextFactory):
        """
        @param reactor: An L{IReactorTCP} provider

        @param host: A hostname, used when connecting
        @type host: str

        @param port: The port number, used when connecting
        @type port: int

        @param torCircuitContextFactory: An instance of
            L{TorCircuitContextFactory}

        This endpoint will be routed through Tor over a circuit whose construction is defined by the torCircuitContextFactory.
        STREAM events 
        """
        self.host = host
        self.port = port
        self.torCircuitContextFactory = torCircuitContextFactory
        self.torCircuitContextFactory.streamAttacher

    def connect(self, protocolFactory):
        """
        Implements L{IStreamClientEndpoint.connect} to connect via TCP, after
        SOCKS5 negotiation and Tor circuit construction is done.
        """

        proxyEndpoint = TCP4ClientEndpoint(reactor, '127.0.0.1', 9050)
        proxyFac = _WrappingFactory(SOCKS5ClientFactory(self.host, self.port, protocolFactory))
        sA = self.torCircuitContextFactory.streamAttacher
        proxyFac._onConnection.addCallback(
                        lambda proto: sA.addLocalStream(proto.transport.getHost()))
        d = proxyEndpoint.connect(proxyFac)
        d.addCallback(lambda proto: proxyFac._wrappedFactory.deferred)
        return d

@implementer(IStreamAttacher)
class MetaAttacher(CircuitListenerMixin, StreamListenerMixin):
    """
    How we use a single Tor instance with multiple stream attachers 
    """
    _streamToAttacherMap = {}
    def __init__(self, state):
        self.state = state
        self.state.set_attacher(self, reactor)
    def attach_stream(self, stream, circuits):
        try:
            key = (str(stream.source_addr), int(stream.source_port))
            return self._streamToAttacherMap[key].attach_stream(stream, circuits)
        except KeyError:
            # No streamAttachers have claimed this stream; default to Tor.
            return None

class SingleExitStreamAttacher(MetaAttacher):
    """
    An instance of this StreamAttacher will attach all streams to
    circuits with the same exit (or fail).
    """
    def __init__(self, state, exit):
        self.state = state
        self.exit = exit
        self.waiting_circuits = {}
        self.expected_streams = {}
        self.built_circuits = {}
        # Needs to listen to both stream and circuit events
        self.state.add_stream_listener(self)
        self.state.add_circuit_listener(self)

    def addLocalStream(self, getHost):
        """
        Add a locally initiated stream to this StreamAttacher
        """
        key = (str(getHost.host),int(getHost.port))
        MetaAttacher._streamToAttacherMap[key] = self
        d = defer.Deferred()
        self.expected_streams[key] = d
        self.request_circuit_build(self.exit, d)

    def attach_stream(self, stream, circuits):
        try:
            key = (str(stream.source_addr), int(stream.source_port))
            return self.expected_streams[key]
        except KeyError:
            # We didn't expect this stream, so let Tor handle it
            return None

    def stream_closed(self, stream, **kw):
        key = (str(stream.source_addr), int(stream.source_port))
        try:
            d = self.expected_streams.pop(key)
            MetaAttacher._streamToAttacherMap.pop(key)
            if not d.called:
                log.debug("Stream:%d Closed before circuit attached!")
            if stream.circuit and stream.circuit.id in self.state.circuits:
                stream.circuit.close(ifUnused=True)
        except KeyError:
            pass

    def circuit_failed(self, circuit, kw):
        if circuit.id in self.waiting_circuits:
            (circ, d, exit) = self.waiting_circuits.pop(circuit.id)
            log.debug("Circuit: %d FAILED. Building new circuit for %s" % (circ.id, exit.id_hex)))
            self.request_circuit_build(self.exit, d)

    def circuit_closed(self, 
        if circuit.id in self.waiting_circuits:
            (circ, d, exit) = self.waiting_circuits.pop(circuit.id)
            log.debug("Circuit: %d closed while in waiting_circuits." % circ.id)
        if circuit.id in self.built_circuits:
            self.built_circuits.pop(circuit.id)

    def circuit_built(self, circuit):
        if circuit.purpose != "GENERAL":
            return

        if circuit.id in self.waiting_circuits:
            circuit, d, exit = self.waiting_circuits.pop(circuit.id)
            assert circuit.path[-1] is exit
            self.built_circuits[circuit.id] = (circuit, d, exit)
            d.callback(circuit)

    def request_circuit_build(self, exit, deferred_to_callback):
        # see if we already have a circuit
        for circ in self.state.circuits.values():
            if (len(circ.path) >= 3) and (circ.path[-1].id_hex == exit.id_hex)  and (circ.state == 'BUILT'):
                log.debug("Re-Using circ %s" % circ)
                deferred_to_callback.callback(circ)
                return

        path = [ random.choice(self.state.entry_guards.values()),
                 random.choice(self.state.routers.values()),
                 self.exit ]
        
        def addToWaitingCircs(circ):
            self.waiting_circuits[circ.id] = (circ, deferred_to_callback, exit)

        self.state.build_circuit(path).addCallback(addToWaitingCircs)

    def __del__(self):
        # Clean up all of the circuits we created
        #XXX: requires txtorcon 0.9.0 (git master)
        try:
            for circ, d, exit in self.built_circuits.values():
                circ.close()
        except AttributeError:
            pass
        super(self).__del__(self)

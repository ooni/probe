from txtorcon import CircuitListenerMixin, IStreamAttacher, StreamListenerMixin
from twisted.web.client import readBody, Agent, SchemeNotSupported
from zope.interface import implementer

from twisted.internet import protocol, defer, reactor, interfaces
from twisted.internet.endpoints import TCP4ClientEndpoint, _WrappingFactory
from txsocksx.client import SOCKS5ClientFactory

from ooni.nettest import NetTestCase
from ooni.settings import config
from ooni.utils import log
from ooni import errors

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
        self.waiting_circuits = []
        self.expected_streams = {}
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

    def circuit_built(self, circuit):
        if circuit.purpose != "GENERAL":
            return
        for (circid, d, exit) in self.waiting_circuits:
            if circid == circuit.id:
                self.waiting_circuits.remove((circid, d, exit))
                d.callback(circuit)

    def request_circuit_build(self, exit, deferred_to_callback):
        # see if we already have a circuit
        for circ in self.state.circuits.values():
            try:
                if (len(circ.path) >= 3) \
                    and (circ.path[-1].id_hex == exit.id_hex) \
                    and (circ.status == 'SUCCEEDED'):
                    return circ
            except AttributeError:
                #XXX: Find out why circ.status is not set
                log.debug("Circuit status not known %s" % circ)

        path = [ random.choice(self.state.entry_guards.values()),
                 random.choice(self.state.routers.values()),
                 self.exit ]
        
        def addToWaitingCircs(circ):
            self.waiting_circuits.append((circ.id, deferred_to_callback, exit))

        self.state.build_circuit(path).addCallback(addToWaitingCircs)

class TorTest(NetTestCase):
    name = "Base Tor Test"
    version = "0.1"
    description = "Base Test for Tor Network Tests"

    def getInputProcessor(self):
        #XXX: doesn't seem that we have any of the exitpolicy available :\
        #XXX: so the circuit might fail if port 80 isn't allowed
        exits = filter(lambda router: 'exit' in router.flags,
                        config.tor_state.routers.values())
        hexes = [exit.id_hex for exit in exits]
        for curse in hexes: yield curse

    def _setUp(self):
        if not config.tor.control_port:
            log.debug("Tor must be running and provide a control port!")
            raise errors.TorControlPortNotFound
        self.state = config.tor_state
        # Add a circuit attacher
        MetaAttacher(self.state)

    def test_fetch_exit_ip(self):
        try:
            exit = self.state.routers[self.input]
        except KeyError:
            # Router not in consensus, sorry
            self.report['failure'] = "Router %s not in consensus." % self.input
            return

        self.report['exit_ip'] = exit.ip
        parent = self

        class OnionRoutedAgent(Agent):
            def _getEndpoint(self, scheme, host, port):
                return parent.getExitSpecificEndpoint((host,port), exit)
        agent = OnionRoutedAgent(reactor)

        d = agent.request('GET', 'http://api.externalip.net/ip/')
        d.addCallback(readBody)

        def addResultToReport(result):
            self.report['external_exit_ip'] = result

        def addFailureToReport(failure):
            self.report['failure'] = errors.handleAllFailures(failure)

        d.addCallback(addResultToReport)
        d.addErrback(addFailureToReport)
        return d

    def getExitSpecificEndpoint(self, addr, exit):
        """
        Returns an OnionRoutedTCPClientEndpoint
        @param exit L{txtorcon.router.Router} of the exit to choose
        @param endpoint 
        """
        host, port = addr
        return OnionRoutedTCPClientEndpoint(reactor, host, port,
                TorCircuitContextFactory(self.state, SingleExitStreamAttacher(self.state, exit)))

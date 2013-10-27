from twisted.internet import reactor
from ooni.nettest import NetTestCase
from ooni.settings import config
from ooni.utils import log
from ooni.utils.tor import OnionRoutedTCPClientEndpoint, TorCircuitContextFactory
from ooni.utils.tor import SingleExitStreamAttacher, MetaAttacher

from ooni import errors

class TorTest(NetTestCase):
    name = "Base Tor Test"
    version = "0.1"
    description = "Base Test for Tor Network Tests"

    def __init__(self):
        self.state = config.tor_state

    def _setUp(self):
        if not config.tor.control_port:
            log.debug("Tor must be running and provide a control port!")
            raise errors.TorControlPortNotFound

        # Add a circuit attacher
        MetaAttacher(self.state)

    def getExitSpecificEndpoint(self, addr, exit):
        """
        Returns an OnionRoutedTCPClientEndpoint
        @param exit L{txtorcon.router.Router} of the exit to choose
        @param endpoint 
        """
        host, port = addr
        return OnionRoutedTCPClientEndpoint(reactor, host, port,
                TorCircuitContextFactory(self.state, SingleExitStreamAttacher(self.state, exit)))

    @property
    def exits(self):
        return filter(lambda r: 'exit' in r.flags and 'badexit' not in r.flags, self.state.routers.values())

    @property
    def guards(self):
        self.state.guards.values()

    def myguards(self):
        self.state.entry_guards.values()

    def exitsToPort(self, port):
        return filter(lambda r: r.accepted_ports and port in r.accepted_ports, self.exits)

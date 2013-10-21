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

    def _setUp(self):
        if not config.tor.control_port:
            log.debug("Tor must be running and provide a control port!")
            raise errors.TorControlPortNotFound
        self.state = config.tor_state
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

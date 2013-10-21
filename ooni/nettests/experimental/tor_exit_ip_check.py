from twisted.web.client import Agent, readBody
from twisted.internet import reactor

from ooni.settings import config
from ooni.templates.tort import TorTest
from ooni.utils import log, tor
from ooni import errors

class TorExitIPTest(TorTest):
    name = "Tor Exit IP Test"
    version = "0.1"
    description = "Fetch the egress IP of Tor Exits"

    def getInputProcessor(self):
        #XXX: doesn't seem that we have any of the exitpolicy available :\
        #XXX: so the circuit might fail if port 80 isn't allowed
        exits = filter(lambda router: 'exit' in router.flags,
                        config.tor_state.routers.values())
        hexes = [exit.id_hex for exit in exits]
        for curse in hexes: yield curse

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

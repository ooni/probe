import random

from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.internet.protocol import Protocol, Factory
from scapy.all import get_if_list
import txtorcon

from ooni.settings import OConfig


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.conf = OConfig()
        self.configuration = {'advanced': {'interface': 'auto',
                                           'start_tor': True},
                              'tor': {}}
        self.silly_listener = None
        self.tor_protocol = None

    def tearDown(self):
        if self.silly_listener is not None:
            self.silly_listener.stopListening()

    def run_tor(self):
        def progress(percent, tag, summary):
            ticks = int((percent/100.0) * 10.0)
            prog = (ticks * '#') + ((10 - ticks) * '.')
            print '%s %s' % (prog, summary)

        config = txtorcon.TorConfig()
        config.SocksPort = self.configuration['tor']['socks_port']
        config.ControlPort = self.configuration['tor']['control_port']
        d = txtorcon.launch_tor(config, reactor, progress_updates=progress)
        return d

    def run_silly_server(self):
        class SillyProtocol(Protocol):
            def __init__(self, factory):
                self.factory = factory

        class SillyFactory(Factory):
            protocol = SillyProtocol

        self.silly_listener = reactor.listenTCP(self.configuration['tor']['socks_port'], SillyFactory())

    @defer.inlineCallbacks
    def test_vanilla_configuration(self):
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, True)

    @defer.inlineCallbacks
    def test_check_incoherences_start_tor_missing_options(self):
        self.configuration['advanced']['start_tor'] = False
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, False)
        self.configuration['tor'] = {'socks_port': 9999}
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, False)
        self.configuration['tor']['control_port'] = 9998
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, False)

    @defer.inlineCallbacks
    def test_check_incoherences_start_tor_correct(self):
        self.configuration['advanced']['start_tor'] = False
        self.configuration['tor'] = {'socks_port': 9999}
        self.configuration['tor']['control_port'] = 9998
        self.tor_process = yield self.run_tor()
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, True)
        self.tor_process.transport.signalProcess('TERM')

        d = defer.Deferred()
        reactor.callLater(10, d.callback, None)
        yield d

    @defer.inlineCallbacks
    def test_check_incoherences_start_tor_silly_listener(self):
        self.configuration['advanced']['start_tor'] = False
        self.configuration['tor'] = {'socks_port': 9999}
        self.configuration['tor']['control_port'] = 9998
        self.run_silly_server()
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, False)

    @defer.inlineCallbacks
    def test_check_incoherences_interface(self):
        self.configuration['advanced']['interface'] = 'funky'
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, False)

        self.configuration['advanced']['interface'] = random.choice(get_if_list())
        ret = yield self.conf.check_incoherences(self.configuration)
        self.assertEqual(ret, True)

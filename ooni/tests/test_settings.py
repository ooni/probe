import random

from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.internet.protocol import Protocol, Factory
from scapy.all import get_if_list
import txtorcon

from ooni.settings import OConfig
from ooni import errors
from bases import ConfigTestCase


class TestSettings(ConfigTestCase):
    def setUp(self):
        super(ConfigTestCase, self).setUp()
        self.conf = OConfig()
        self.configuration = {'advanced': {'interface': 'auto',
                                           'start_tor': True},
                              'tor': {}}
        self.silly_listener = None
        self.tor_protocol = None

    def tearDown(self):
        super(ConfigTestCase, self).tearDown()
        if self.silly_listener is not None:
            self.silly_listener.stopListening()

    def run_tor(self):
        def progress(percent, tag, summary):
            ticks = int((percent/100.0) * 10.0)
            prog = (ticks * '#') + ((10 - ticks) * '.')
            print '%s %s' % (prog, summary)

        config = txtorcon.TorConfig()
        config.SocksPort = self.conf.tor.socks_port
        config.ControlPort = self.conf.tor.control_port
        d = txtorcon.launch_tor(config, reactor, progress_updates=progress)
        return d

    def run_silly_server(self):
        class SillyProtocol(Protocol):
            def __init__(self, factory):
                self.factory = factory

        class SillyFactory(Factory):
            protocol = SillyProtocol

        self.silly_listener = reactor.listenTCP(self.conf.tor.socks_port, SillyFactory())

    def test_vanilla_configuration(self):
        self.conf.check_incoherences(self.configuration)

    @defer.inlineCallbacks
    def test_check_tor_missing_options(self):
        self.conf.advanced.start_tor = False
        try:
            yield self.conf.check_tor()
        except errors.ConfigFileIncoherent:
            pass

        self.conf.tor.socks_port = 9999
        try:
            yield self.conf.check_tor()
        except errors.ConfigFileIncoherent:
            pass

        self.conf.tor.socks_port = None
        self.conf.tor.control_port = 9998
        try:
            yield self.conf.check_tor()
        except errors.ConfigFileIncoherent:
            pass

    @defer.inlineCallbacks
    def test_check_tor_correct(self):
        self.conf.advanced.start_tor = False
        self.conf.tor.socks_port = 9999
        self.conf.tor.control_port = 9998
        self.tor_process = yield self.run_tor()
        yield self.conf.check_incoherences(self.configuration)
        self.tor_process.transport.signalProcess('TERM')

        d = defer.Deferred()
        reactor.callLater(10, d.callback, None)
        yield d

    @defer.inlineCallbacks
    def test_check_tor_silly_listener(self):
        self.conf.advanced.start_tor = False
        self.conf.tor.socks_port = 9999
        self.conf.tor.control_port = 9998
        self.run_silly_server()
        try:
            yield self.conf.check_tor()
        except errors.ConfigFileIncoherent:
            pass

    def test_check_incoherences_interface(self):
        self.configuration['advanced']['interface'] = 'funky'
        self.assertRaises(errors.ConfigFileIncoherent, self.conf.check_incoherences, self.configuration)

        self.configuration['advanced']['interface'] = random.choice(get_if_list())
        self.conf.check_incoherences(self.configuration)

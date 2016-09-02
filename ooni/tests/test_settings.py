import os
import random
import tempfile

import yaml

from twisted.internet import defer, reactor
from twisted.internet.protocol import Protocol, Factory
from scapy.all import get_if_list
import txtorcon

from ooni.settings import OConfig
from ooni import errors
from ooni.utils import net
from bases import ConfigTestCase

from ooni.settings import _load_config_files_with_defaults

class TestSettings(ConfigTestCase):
    def setUp(self):
        super(TestSettings, self).setUp()
        self.conf = OConfig()
        self.configuration = {'advanced': {'interface': 'auto',
                                           'start_tor': True},
                              'tor': {}}
        self.silly_listener = None
        self.tor_protocol = None

    def tearDown(self):
        super(TestSettings, self).tearDown()
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

            def buildProtocol(self, address):
                p = self.protocol(self)
                return p

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
        """
        This test has been disabled because there is a strange concatenation of
        conditions that make it not possible to run it on travis.
        The tests need to be run as root on travis so that the ones that use
        scapy will work properly. When running tor as root, though, it will by
        default drop privileges to a lesser priviledged user (on debian based
        systems debian-tor). The problem is that the datadir will have already
        been created with the privileges of root, hence it will fail to use it
        as a datadir and fail.
        txtorcon addressed this issue in https://github.com/meejah/txtorcon/issues/26
        by chmodding the datadir with what is set as User.
        So we could either:

            1) Set User to root so that tor has access to that directory, but
            this will not work because then it will not be happy that
            /var/run/tor has more lax permissions (also debian-tor can read it)
            so it will fail. We could disable the control port, hence not
            needing to use /var/run/tor, but this is not possible due to:
            https://github.com/meejah/txtorcon/issues/80

            2) We set the User to be the owner of /var/run/tor, but this does
            not exist on all systems, so it would only work for travis.

        For the time being I am just going to disable this test and wait for
        one of the above bugs to have a better fix.
        """
        self.skipTest("See comment in the code")
        self.conf.advanced.start_tor = False
        self.conf.tor.socks_port = net.randomFreePort()
        self.conf.tor.control_port = net.randomFreePort()
        self.tor_process = yield self.run_tor()
        yield self.conf.check_incoherences(self.configuration)
        self.tor_process.transport.signalProcess('TERM')

        d = defer.Deferred()
        reactor.callLater(10, d.callback, None)
        yield d

    @defer.inlineCallbacks
    def test_check_tor_silly_listener(self):
        self.conf.advanced.start_tor = False
        self.conf.tor.socks_port = net.randomFreePort()
        self.conf.tor.control_port = None
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


    def test_load_config_files(self):
        defaults = {
            'cat1': {
                'key': 'value'
            },
            'cat2': {
                'key': 'value',
                'key2': 'value2'
            },
            'cat3': {
                'key': 'value'
            }
        }
        config_file_A = {
            'cat1': {
                'key': 'valueA'
            },
            'cat2': {
                'key': 'valueA',
                'invalid_key': 'ignored'
            },
            'invalid_category': {
                'ignored': 'ignored'
            },
            'cat3': None
        }
        config_file_B = {
            'cat1': {
                'key': 'valueB'
            },
            'cat2': {
                'key2': 'value2B'
            }
        }
        temp_dir = tempfile.mkdtemp()
        config_file_A_path = os.path.join(temp_dir, "configA.conf")
        config_file_B_path = os.path.join(temp_dir, "configB.conf")
        with open(config_file_A_path, 'w') as out_file:
            yaml.safe_dump(config_file_A, out_file)

        with open(config_file_B_path, 'w') as out_file:
            yaml.safe_dump(config_file_B, out_file)

        config = _load_config_files_with_defaults([config_file_B_path,
                                                   '/invalid/path/ignored.txt',
                                                   config_file_A_path],
                                                  defaults)

        self.assertEqual(config, {
            'cat1': {
                'key': 'valueB'
            },
            'cat2': {
                'key': 'valueA',
                'key2': 'value2B'
            },
            'cat3': {
                'key': 'value'
            }
        })

#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# 
#  +-----------+
#  |  BRIDGET  |
#  |        +----------------------------------------------+
#  +--------| Use a slave Tor process to test making a Tor |
#           | connection to a list of bridges or relays.   |
#           +----------------------------------------------+
#
# :authors: Arturo Filasto, Isis Lovecruft, Jacob Appelbaum
# :licence: see included LICENSE
# :version: 0.1.0-alpha

from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import reactor

from ooni.utils import log
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset

class bridgetArgs(usage.Options):
    optParameters = [['bridges', 'b', None, 'List of bridges to scan'],
                     ['relays', 'f', None, 'List of relays to scan'],
                     ['resume', 'r', 0, 'Resume at this index']]

class bridgetTest(OONITest):
    implements(IPlugin, ITest)

    shortName = "bridget"
    description = "Use a slave Tor process to test RELAY_EXTEND to bridges/relays"
    requirements = None
    options = bridgetArgs
    blocking = False

    def experiment(self, args):
        log.msg("BridgeT: initiating test ... ")

        from ooni.lib.txtorcon import TorProtocolFactory, TorConfig, TorState
        from ooni.lib.txtorcon import DEFAULT_VALUE, launch_tor

        reactor = self.reactor

        def setup_failed(args):
            log.msg("Setup Failed.")
            report.update({'failed': args})
            reactor.stop()
            #return report

        def setup_complete(proto):
            log.msg("Setup Complete: %s" % proto)
            state = TorState(proto.tor_protocol)
            state.post_bootstrap.addCallback(state_complete).addErrback(setup_failed)
            report.update({'success': args})
            #return report

        def bootstrap(c):
            conf = TorConfig(c)
            conf.post_bootstrap.addCallback(setup_complete).addErrback(setup_failed)
            log.msg("Slave Tor process connected, bootstrapping ...")

        config = TorConfig()
        import random
        config.SocksPort = random.randint(1024, 2**16)
        config.ControlPort = random.randint(1024, 2**16)
        #config.SocksPort = 12345
        #config.ControlPort = 12346

        if 'bridge' in args:
            config.UseBridges = 1
            config.Bridge = args['bridge']
        config.save()
        print config.create_torrc()
        report = {'tor_config': config.config}
        log.msg("Starting Tor")

        def updates(prog, tag, summary):
            log.msg("%d%%: %s" % (prog, summary))
            #return

        d = launch_tor(config, self.reactor, progress_updates=updates)
        d.addCallback(setup_complete)
        d.addErrback(setup_failed)
        return d

    def load_assets(self):
        assets = {}
        if self.local_options:
            if self.local_options['bridges']:
                assets.update({'bridge': Asset(self.local_options['bridges'])})
            elif self.local_options['relays']:
                assets.update({'relay': Asset(self.local_options['relays'])})
        return assets

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
bridget = bridgetTest(None, None, None)

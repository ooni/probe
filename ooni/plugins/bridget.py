"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import reactor

from ooni import log
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset

class bridgetArgs(usage.Options):
    optParameters = [['bridges', 'b', None, 'List of bridges to scan'],
                     ['relays', 'f', None, 'List of relays to scan'],
                     ['resume', 'r', 0, 'Resume at this index']]

class bridgetTest(OONITest):
    implements(IPlugin, ITest)

    shortName = "bridget"
    description = "bridget"
    requirements = None
    options = bridgetArgs
    blocking = False

    def experiment(self, args):
        log.msg("Doing test")
        # What you return here gets handed as input to control
        from ooni.lib.txtorcon import TorProtocolFactory, TorConfig, TorState
        from ooni.lib.txtorcon import DEFAULT_VALUE, launch_tor
        def updates(prog, tag, summary):
            log.msg("%d%%: %s" % (prog, summary))

        def setup_failed(args):
            log.msg("Setup Failed.")
            report.update({'failed': args})
            return report

        def setup_complete(proto):
            log.msg("Setup Complete.")
            report.update({'success': args})
            return report

        config = TorConfig()
        config.SocksPort = 9999
        config.OrPort = 1234
        if 'bridge' in args:
            config.UseBridges = 1
            config.Bridge = args['bridge']
        config.save()
        report = {'tor_config': config.config}
        log.msg("Starting Tor")
        d = launch_tor(config, reactor, progress_updates=updates)
        d.addCallback(setup_complete)
        d.addErrback(setup_failed)
        return d

    def load_assets(self):
        assets = {}
        if self.local_options:
            if self.local_options['bridges']:
                assets.update({'bridge': Asset(self.local_options['bridges'])})
            elif self.local_options['relays']:
                assets.update({'relay': Asset(self.local_options['relay'])})
        return assets

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
bridget = bridgetTest(None, None, None)

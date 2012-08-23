"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
from exceptions import Exception
from datetime import datetime
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import reactor, task

from ooni.utils import log
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset

from ooni.lib.txtorcon import TorProtocolFactory, TorConfig, TorState
from ooni.lib.txtorcon import DEFAULT_VALUE, launch_tor

class bridgetArgs(usage.Options):
    optParameters = [['bridges', 'b', None, 'List of bridges to scan'],
                     ['relays', 'f', None, 'List of relays to scan'],
                     ['resume', 'r', 0, 'Resume at this index'],
                     ['timeout', 't', 5, 'Timeout in seconds after which to consider a bridge not working']
                    ]

class bridgetTest(OONITest):
    implements(IPlugin, ITest)

    shortName = "bridget"
    description = "bridget"
    requirements = None
    options = bridgetArgs
    blocking = False

    def experiment(self, args):
        log.msg("Doing test")
        last_update = datetime.now()
        tor_log = []

        def check_timeout():
            log.msg("Checking for timeout")
            time_since_update = datetime.now() - last_update
            if time_since_update.seconds > self.local_options['timeout']:
                log.msg("Timed out when connecting to %s" % args)
                l.stop()
                self.result['reason'] = 'timeout'
                d.errback(args)
            return

        def updates(prog, tag, summary):
            tor_log.append((prog, tag, summary))
            last_update = datetime.now()
            log.msg("%d%%: %s" % (prog, summary))

        def setup_failed(failure):
            log.msg("Setup Failed.")
            if not self.result['reason']:
                self.result['reason'] = 'unknown'
            self.result['input'] = args
            self.result['result'] = 'failed'
            self.result['tor_log'] = tor_log
            return

        def setup_complete(proto):
            log.msg("Setup Complete.")
            self.result['input'] = args
            self.result['result'] = 'success'
            return

        config = TorConfig()
        import random
        config.SocksPort = random.randint(1024, 2**16)
        config.ControlPort = random.randint(1024, 2**16)

        if 'bridge' in args:
            config.UseBridges = 1
            config.Bridge = args['bridge']

        config.save()

        print config.config
        self.result['tor_config'] = config.config
        log.msg("Starting Tor connecting to %s" % args['bridge'])

        l = task.LoopingCall(check_timeout)
        l.start(1.0)

        d = launch_tor(config, self.reactor, control_port=config.ControlPort, progress_updates=updates)
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

import random

from twisted.python import usage
from twisted.internet import defer

import txtorcon
from txtorcon.torconfig import TorSetupTimeout

from ooni.utils import log
from ooni import nettest

class UsageOptions(usage.Options):
    optParameters = [['timeout', 't', 30,
                      'Specify the timeout after which to consider the Tor bootstrapping process to have failed']
                    ]

class KeywordFiltering(nettest.NetTestCase):
    name = "Bridget, at it's bare minimum"
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
            'File containing bridges to test reachability for (they should be one per line IP:ORPort)']

    def setUp(self):
        self.tor_progress = 0
        self.timeout = int(self.localOptions['timeout'])
        self.report['timeout'] = self.timeout

    def test_full_tor_connection(self):
        config = txtorcon.TorConfig()
        config.OrPort = random.randint(2**14, 2**16)
        config.SocksPort = random.randint(2**14, 2**16)
        config.Bridge = self.input
        config.UseBridges = 1

        def updates(prog, tag, summary):
            self.report['tor_progress'] = int(prog)

        d = txtorcon.launch_tor(config, reactor, progress_updates=updates, self.timeout)
        @d.addCallback
        def setup_complete(proto):
            self.report['failed'] = False

        @d.addErrback
        def setup_failed(failure):
            failure.trap(TorSetupTimeout)
            if isinstance(failure, TorSetupTimeout):
                self.report['failure'] = 'timedout'
            else:
                self.report['failure'] = 'unknown'
            self.report['failed'] = True

        return d

    def test_connect_scan(self):
        pass

# -*- encoding: utf-8 -*-
import random
import string
import subprocess

from twisted.python import usage
from twisted.internet import defer, reactor

import txtorcon

from ooni.utils import log
from ooni import nettest

class UsageOptions(usage.Options):
    optParameters = [['timeout', 't', 60,
                      'Specify the timeout after which to consider the Tor bootstrapping process to have failed'],
                    ]

class KeywordFiltering(nettest.NetTestCase):
    name = "BridgetKISS"
    author = "Arturo Filastò"
    version = "0.1"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
            'File containing bridges to test reachability for (they should be one per line IP:ORPort)']

    def setUp(self):

        def find_pyobfsproxy():
            try:
                proc = subprocess.Popen(('type -p pyobfsproxy', ), stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, shell=True)
            except OSError:
                pass
            else:
                stdout, _ = proc.communicate()
                if proc.poll() == 0 and stdout != '':
                    return stdout.strip()

        self.tor_progress = 0
        self.timeout = int(self.localOptions['timeout'])
        self.report['timeout'] = self.timeout
        self.bridge = self.input
        self.pyobfsproxy_bin = find_pyobfsproxy()

    def test_full_tor_connection(self):
        def getTransport(address):
            """
            If the address of the bridge starts with a valid c identifier then
            we consider it to be a bridge.
            Returns:
                The transport_name if it's a transport.
                None if it's not a obfsproxy bridge.
            """
            transport_name = address.split(' ')[0]
            transport_name_chars = string.ascii_letters + string.digits
            if all(c in transport_name_chars for c in transport_name):
                return transport_name
            else:
                return None

        config = txtorcon.TorConfig()
        config.ControlPort = random.randint(2**14, 2**16)
        config.SocksPort = random.randint(2**14, 2**16)

        transport_name = getTransport(self.bridge)
        if transport_name and self.pyobfsproxy_bin:
            config.ClientTransportPlugin = "%s exec %s managed" % (transport_name, self.pyobfsproxy_bin)
            self.report['transport_name'] = transport_name
        elif transport_name and not self.pyobfsproxy_bin:
            log.err("Unable to test bridge because pyobfsproxy is not installed")
            self.report['success'] = None
            return

        config.Bridge = self.bridge
        config.UseBridges = 1
        config.save()

        def updates(prog, tag, summary):
            print "Tor progress: %s%%" % prog
            self.report['tor_progress'] = int(prog)
            self.report['tor_progress_tag'] = tag
            self.report['tor_progress_summary'] = summary

        d = txtorcon.launch_tor(config, reactor, timeout=self.timeout,
                progress_updates=updates)
        @d.addCallback
        def setup_complete(proto):
            print "Success"
            self.report['success'] = True

        @d.addErrback
        def setup_failed(failure):
            print "Failed"
            log.exception(failure)
            self.report['success'] = False

        return d

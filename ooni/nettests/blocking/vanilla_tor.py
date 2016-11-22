# -*- encoding: utf-8 -*-
import os
import tempfile
import shutil

from twisted.python import usage
from twisted.internet import reactor, error

import txtorcon

from ooni.utils import log, onion, net
from ooni import nettest


class TorIsNotInstalled(Exception):
    pass


class UsageOptions(usage.Options):
    optParameters = [
        ['timeout', 't', 300,
         'Specify the timeout after which to consider '
         'the Tor bootstrapping process to have failed.'], ]


class VanillaTor(nettest.NetTestCase):
    name = "Vanilla Tor"
    description = "A test for checking if vanilla Tor connections work."
    author = "Arturo Filastò"
    version = "0.1.0"

    usageOptions = UsageOptions

    def requirements(self):
        if not onion.find_tor_binary():
            raise TorIsNotInstalled(
                "For instructions on installing Tor see: "
                "https://www.torproject.org/download/download")

    def setUp(self):
        self.tor_progress = 0
        self.timeout = int(self.localOptions['timeout'])

        fd, self.tor_logfile = tempfile.mkstemp()
        os.close(fd)
        self.tor_datadir = tempfile.mkdtemp()

        self.report['error'] = None
        self.report['success'] = None
        self.report['timeout'] = self.timeout
        self.report['transport_name'] = 'vanilla'
        self.report['tor_version'] = str(onion.tor_details['version'])
        self.report['tor_progress'] = 0
        self.report['tor_progress_tag'] = None
        self.report['tor_progress_summary'] = None
        self.report['tor_log'] = None

    def test_full_tor_connection(self):
        config = txtorcon.TorConfig()
        config.ControlPort = net.randomFreePort()
        config.SocksPort = net.randomFreePort()
        config.DataDirectory = self.tor_datadir
        log.msg(
            "Connecting to tor %s" %
            (onion.tor_details['version']))

        config.log = ['notice stdout', 'notice file %s' % self.tor_logfile]
        config.save()

        def updates(prog, tag, summary):
            log.msg("Progress is at: %s%%" % (prog))
            self.report['tor_progress'] = int(prog)
            self.report['tor_progress_tag'] = tag
            self.report['tor_progress_summary'] = summary

        d = txtorcon.launch_tor(config, reactor, timeout=self.timeout,
                                progress_updates=updates)

        @d.addCallback
        def setup_complete(proto):
            try:
                proto.transport.signalProcess('TERM')
            except error.ProcessExitedAlready:
                proto.transport.loseConnection()
            log.msg("Successfully connected to Tor")
            self.report['success'] = True

        @d.addErrback
        def setup_failed(failure):
            log.msg("Failed to connect to Tor")
            self.report['success'] = False
            self.report['error'] = 'timeout-reached'
            return

        @d.addCallback
        def write_log(_):
            with open(self.tor_logfile) as f:
                self.report['tor_log'] = f.read()
            os.remove(self.tor_logfile)
            try:
                shutil.rmtree(self.tor_datadir)
            except:
                pass

        return d

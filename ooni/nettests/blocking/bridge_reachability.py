# -*- encoding: utf-8 -*-
import os
import random
import tempfile
import shutil

from twisted.python import usage
from twisted.internet import reactor, error

import txtorcon

from ooni.utils import log, onion
from ooni import nettest


class TorIsNotInstalled(Exception):
    pass


class UsageOptions(usage.Options):
    optParameters = [
        ['timeout', 't', 120,
         'Specify the timeout after which to consider '
         'the Tor bootstrapping process to have failed.'], ]


class BridgeReachability(nettest.NetTestCase):
    name = "Bridge Reachability"
    description = "A test for checking if bridges are reachable " \
                  "from a given location."
    author = "Arturo Filastò"
    version = "0.1.2"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'File containing bridges to test reachability for. '
                 'They should be one per line IP:ORPort or '
                 'TransportType IP:ORPort (ex. obfs2 127.0.0.1:443).']

    requiredOptions = ['file']

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
        fd, self.obfsproxy_logfile = tempfile.mkstemp()
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
        self.report['obfsproxy_version'] = str(onion.obfsproxy_details['version'])
        self.report['obfsproxy_log'] = None
        self.report['bridge_address'] = None

        self.bridge = self.input
        if self.input.startswith('Bridge'):
            self.bridge = self.input.replace('Bridge ', '')

    def postProcessor(self, measurements):
        if 'successes' not in self.summary:
            self.summary['successes'] = []
        if 'failures' not in self.summary:
            self.summary['failures'] = []

        details = {
            'address': self.report['bridge_address'],
            'transport_name': self.report['transport_name'],
            'tor_progress': self.report['tor_progress']
        }
        if self.report['success']:
            self.summary['successes'].append(details)
        else:
            self.summary['failures'].append(details)
        return self.report

    def displaySummary(self, summary):
        successful_count = {}
        failure_count = {}

        def count(results, counter):
            for result in results:
                if result['transport_name'] not in counter:
                    counter[result['transport_name']] = 0
                counter[result['transport_name']] += 1
        count(summary['successes'], successful_count)
        count(summary['failures'], failure_count)

        working_bridges = ', '.join(
            ["%s %s" % (x['transport_name'], x['address'])
             for x in summary['successes']])
        failing_bridges = ', '.join(
            ["%s %s (at %s%%)"
             % (x['transport_name'], x['address'], x['tor_progress'])
             for x in summary['failures']])

        log.msg("Total successes: %d" % len(summary['successes']))
        log.msg("Total failures: %d" % len(summary['failures']))

        for transport, count in successful_count.items():
            log.msg("%s successes: %d" % (transport.title(), count))
        for transport, count in failure_count.items():
            log.msg("%s failures: %d" % (transport.title(), count))

        log.msg("Working bridges: %s" % working_bridges)
        log.msg("Failing bridges: %s" % failing_bridges)

    def test_full_tor_connection(self):
        config = txtorcon.TorConfig()
        config.ControlPort = random.randint(2**14, 2**16)
        config.SocksPort = random.randint(2**14, 2**16)
        config.DataDirectory = self.tor_datadir
        log.msg(
            "Connecting to %s with tor %s" %
            (self.bridge, onion.tor_details['version']))

        transport_name = onion.transport_name(self.bridge)
        if transport_name == None:
            self.report['bridge_address'] = self.bridge.split(' ')[0]
        else:
            self.report['bridge_address'] = self.bridge.split(' ')[1]
            self.report['transport_name'] = transport_name

            try:
                config.ClientTransportPlugin = \
                        onion.bridge_line(transport_name, self.obfsproxy_logfile)
            except onion.UnrecognizedTransport:
                log.err("Unable to test bridge because we don't recognize "
                        "the %s transport" % transport_name)
                self.report['error'] = "unrecognized-transport"
                return
            except onion.UninstalledTransport:
                bin_name = onion.transport_bin_name.get(transport_name)
                log.err("Unable to test bridge because %s is not installed" %
                        bin_name)
                self.report['error'] = "missing-%s" % bin_name
                return
            except onion.OutdatedObfsproxy:
                log.err("The obfsproxy version you are using " \
                        "appears to be outdated.")
                self.report['error'] = 'old-obfsproxy'
                return
            except onion.OutdatedTor:
                log.err("Unsupported Tor version.")
                self.report['error'] = 'unsupported-tor-version'
                return

            log.debug("Using ClientTransportPlugin '%s'" % \
                      config.ClientTransportPlugin)

        config.Bridge = self.bridge
        config.UseBridges = 1
        config.log = ['notice stdout', 'notice file %s' % self.tor_logfile]
        config.save()

        def updates(prog, tag, summary):
            log.msg("%s: %s%%" % (self.bridge, prog))
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
            log.msg("Successfully connected to %s" % self.bridge)
            self.report['success'] = True

        @d.addErrback
        def setup_failed(failure):
            log.msg("Failed to connect to %s" % self.bridge)
            self.report['success'] = False
            self.report['error'] = 'timeout-reached'
            return

        @d.addCallback
        def write_log(_):
            with open(self.tor_logfile) as f:
                self.report['tor_log'] = f.read()
            os.remove(self.tor_logfile)
            with open(self.obfsproxy_logfile) as f:
                self.report['obfsproxy_log'] = f.read()
            os.remove(self.obfsproxy_logfile)
            try:
                with open(os.path.join(self.tor_datadir,
                        'pt_state', 'obfs4proxy.log')) as f:
                    self.report['obfsproxy_log'] = f.read()
            except:
                pass
            finally:
                shutil.rmtree(self.tor_datadir)

        return d

# -*- encoding: utf-8 -*-
import random
from distutils.spawn import find_executable

from twisted.python import usage
from twisted.internet import reactor, error

import txtorcon

from ooni.settings import config
from ooni.utils import log, onion
from ooni import nettest, errors


class TorIsNotInstalled(Exception):
    pass


class UsageOptions(usage.Options):
    optParameters = [
        ['timeout', 't', 120,
         'Specify the timeout after which to consider '
         'the Tor bootstrapping process to have failed'], ]


class BridgeReachability(nettest.NetTestCase):
    name = "Bridge Reachability"
    description = "A test for checking if bridges are reachable " \
                  "from a given location."
    author = "Arturo Filastò"
    version = "0.1.1"

    usageOptions = UsageOptions

    inputFile = ['file', 'f', None,
                 'File containing bridges to test reachability for. '
                 'They should be one per line IP:ORPort or '
                 'TransportType IP:ORPort (ex. obfs2 127.0.0.1:443)']

    requiredOptions = ['file']

    def requirements(self):
        if not onion.find_tor_binary():
            raise TorIsNotInstalled(
                "For instructions on installing Tor see: "
                "https://www.torproject.org/download/download")

    def setUp(self):
        self.tor_progress = 0
        self.timeout = int(self.localOptions['timeout'])

        if self.timeout > config.advanced.measurement_timeout:
            log.err("The measurement timeout is less than the bridge reachability test timeout")
            log.err("Adjust your ooniprobe.conf file by setting the "
                    "advanced: measurement_timeout: value to %d" % self.timeout)
            raise errors.InvalidConfigFile("advanced->measurement_timeout < %d" % self.timeout)

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
        self.report['bridge_address'] = None

        self.bridge = self.input
        if self.input.startswith('Bridge'):
            self.bridge = self.input.replace('Bridge ', '')
        self.pyobfsproxy_bin = onion.obfsproxy_details['binary']
        self.fteproxy_bin = find_executable('fteproxy')

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
        log.msg(
            "Connecting to %s with tor %s" %
            (self.bridge, onion.tor_details['version']))

        transport_name = onion.transport_name(self.bridge)
        if transport_name and transport_name == 'fte' and self.fteproxy_bin:
            config.ClientTransportPlugin = "%s exec %s --managed" % (
                transport_name, self.fteproxy_bin)
            log.debug("Using fte from %s" % self.fteproxy_bin)
            self.report['transport_name'] = transport_name
            self.report['bridge_address'] = self.bridge.split(' ')[1]
        elif transport_name and transport_name == 'fte'\
                and not self.fteproxy_bin:
            log.err("Unable to test bridge because fteproxy is not installed")
            self.report['error'] = 'missing-fteproxy'
            return
        elif transport_name and self.pyobfsproxy_bin:
            config.ClientTransportPlugin = "%s exec %s managed" % (
                transport_name, self.pyobfsproxy_bin)
            if onion.OBFSProxyVersion('0.2') > onion.obfsproxy_details['version']:
                log.err(
                    "The obfsproxy version you are using appears to be outdated."
                )
                self.report['error'] = 'old-obfsproxy'
                return
            log.debug("Using pyobfsproxy from %s" % self.pyobfsproxy_bin)
            self.report['transport_name'] = transport_name
            self.report['bridge_address'] = self.bridge.split(' ')[1]
        elif transport_name and not self.pyobfsproxy_bin:
            log.err(
                "Unable to test bridge because pyobfsproxy is not installed")
            self.report['error'] = 'missing-pyobfsproxy'
            return
        else:
            self.report['bridge_address'] = self.bridge.split(' ')[0]

        if transport_name and transport_name == 'scramblesuit' and \
                onion.TorVersion('0.2.5.1') > onion.tor_details['version']:
            self.report['error'] = 'unsupported-tor-version'
            log.err("Unsupported Tor version.")
            return
        elif transport_name and \
                onion.TorVersion('0.2.4.1') > onion.tor_details['version']:
            self.report['error'] = 'unsupported-tor-version'
            log.err("Unsupported Tor version.")
            return

        config.Bridge = self.bridge
        config.UseBridges = 1
        config.log = 'notice'
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
            self.report['tor_log'] = failure.value.message
            self.report['success'] = False

        return d

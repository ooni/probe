import sys
import os

from ooni import config
from ooni.managers import ReportEntryManager, MeasurementManager
from ooni.reporter import Report
from ooni.utils import log, checkForRoot, NotRootError
from ooni.utils.net import randomFreePort
from ooni.nettest import NetTest
from ooni.errors import UnableToStartTor

from txtorcon import TorConfig
from txtorcon import TorState, launch_tor

from twisted.internet import defer, reactor

class Director(object):
    """
    Singleton object responsible for coordinating the Measurements Manager and the
    Reporting Manager.

    How this all looks like is as follows:

    +------------------------------------------------+
    |                   Director                     |<--+
    +------------------------------------------------+   |
        ^                                ^               |
        |        Measurement             |               |
    +---------+  [---------]    +--------------------+   |
    |         |                 | MeasurementManager |   |
    | NetTest |  [---------]    +--------------------+   |
    |         |                 | [----------------] |   |
    +---------+  [---------]    | [----------------] |   |
        |                       | [----------------] |   |
        |                       +--------------------+   |
        v                                                |
    +---------+   ReportEntry                            |
    |         |   [---------]    +--------------------+  |
    |  Report |                  | ReportEntryManager |  |
    |         |   [---------]    +--------------------+  |
    +---------+                  | [----------------] |  |
                  [---------]    | [----------------] |--
                                 | [----------------] |
                                 +--------------------+

    [------------] are Tasks

    +------+
    |      |  are TaskManagers
    +------+
    |      |
    +------+

    +------+
    |      |  are general purpose objects
    +------+

    """
    _scheduledTests = 0

    def __init__(self):
        self.netTests = []
        self.activeNetTests = []

        self.measurementManager = MeasurementManager()
        self.measurementManager.director = self

        self.reportEntryManager = ReportEntryManager()
        self.reportEntryManager.director = self

        self.successfulMeasurements = 0
        self.failedMeasurements = 0

        self.totalMeasurements = 0

        # The cumulative runtime of all the measurements
        self.totalMeasurementRuntime = 0

        self.failures = []

        self.torControlProtocol = None

    def start(self):
        if config.privacy.includepcap:
            log.msg("Starting")
            if not config.reports.pcap:
                config.generatePcapFilename()
            self.startSniffing()

        if config.advanced.start_tor:
            log.msg("Starting Tor...")
            d = self.startTor()
        else:
            d = defer.succeed(None)
        return d

    @property
    def measurementSuccessRatio(self):
        if self.totalMeasurements == 0:
            return 0

        return self.successfulMeasurements / self.totalMeasurements

    @property
    def measurementFailureRatio(self):
        if self.totalMeasurements == 0:
            return 0

        return self.failedMeasurements / self.totalMeasurements

    @property
    def measurementSuccessRate(self):
        """
        The speed at which tests are succeeding globally.

        This means that fast tests that perform a lot of measurements will
        impact this value quite heavily.
        """
        if self.totalMeasurementRuntime == 0:
            return 0

        return self.successfulMeasurements / self.totalMeasurementRuntime

    @property
    def measurementFailureRate(self):
        """
        The speed at which tests are failing globally.
        """
        if self.totalMeasurementRuntime == 0:
            return 0

        return self.failedMeasurements / self.totalMeasurementRuntime

    def measurementTimedOut(self, measurement):
        """
        This gets called every time a measurement times out independenty from
        the fact that it gets re-scheduled or not.
        """
        pass

    def measurementStarted(self, measurement):
        self.totalMeasurements += 1

    def measurementSucceeded(self, measurement):
        log.msg("Successfully completed measurement: %s" % measurement)
        self.totalMeasurementRuntime += measurement.runtime
        self.successfulMeasurements += 1
        return measurement.testInstance.report

    def measurementFailed(self, failure, measurement):
        log.msg("Failed doing measurement: %s" % measurement)
        self.totalMeasurementRuntime += measurement.runtime

        self.failedMeasurements += 1
        self.failures.append((failure, measurement))
        return failure

    def reporterFailed(self, failure, net_test):
        """
        This gets called every time a reporter is failing and has been removed
        from the reporters of a NetTest.
        Once a report has failed to be created that net_test will never use the
        reporter again.

        XXX hook some logic here.
        note: failure contains an extra attribute called failure.reporter
        """
        pass

    def netTestDone(self, result, net_test):
        self.activeNetTests.remove(net_test)

    def startNetTest(self, _, net_test_loader, reporters):
        """
        Create the Report for the NetTest and start the report NetTest.

        Args:
            net_test_loader:
                an instance of :class:ooni.nettest.NetTestLoader

            _: #XXX very dirty hack
        """
        report = Report(reporters, self.reportEntryManager)

        net_test = NetTest(net_test_loader, report)
        net_test.director = self
        net_test.report.open()

        self.measurementManager.schedule(net_test.generateMeasurements())

        self.activeNetTests.append(net_test)
        net_test.done.addBoth(self.netTestDone, net_test)
        net_test.done.addBoth(report.close)
        return net_test.done

    def startSniffing(self):
        """ Start sniffing with Scapy. Exits if required privileges (root) are not
        available.
        """
        from ooni.utils.txscapy import ScapyFactory, ScapySniffer
        try:
            checkForRoot()
        except NotRootError:
            print "[!] Includepcap options requires root priviledges to run"
            print "    you should run ooniprobe as root or disable the options in ooniprobe.conf"
            sys.exit(1)

        print "Starting sniffer"
        config.scapyFactory = ScapyFactory(config.advanced.interface)

        if os.path.exists(config.reports.pcap):
            print "Report PCAP already exists with filename %s" % config.reports.pcap
            print "Renaming files with such name..."
            pushFilenameStack(config.reports.pcap)

        sniffer = ScapySniffer(config.reports.pcap)
        config.scapyFactory.registerProtocol(sniffer)


    def startTor(self):
        """ Starts Tor
        Launches a Tor with :param: socks_port :param: control_port
        :param: tor_binary set in ooniprobe.conf
        """
        @defer.inlineCallbacks
        def state_complete(state):
            config.tor_state = state
            log.msg("Successfully bootstrapped Tor")
            log.debug("We now have the following circuits: ")
            for circuit in state.circuits.values():
                log.debug(" * %s" % circuit)

            socks_port = yield state.protocol.get_conf("SocksPort")
            control_port = yield state.protocol.get_conf("ControlPort")
            client_ip = yield state.protocol.get_info("address")

            config.tor.socks_port = int(socks_port.values()[0])
            config.tor.control_port = int(control_port.values()[0])

            config.probe_ip = client_ip.values()[0]

            log.debug("Obtained our IP address from a Tor Relay %s" % config.probe_ip)

        def setup_failed(failure):
            log.exception(failure)
            raise UnableToStartTor

        def setup_complete(proto):
            """
            Called when we read from stdout that Tor has reached 100%.
            """
            log.debug("Building a TorState")
            state = TorState(proto.tor_protocol)
            state.post_bootstrap.addCallback(state_complete)
            state.post_bootstrap.addErrback(setup_failed)
            return state.post_bootstrap

        def updates(prog, tag, summary):
            log.debug("%d%%: %s" % (prog, summary))

        tor_config = TorConfig()
        if config.tor.control_port:
            tor_config.ControlPort = config.tor.control_port
        else:
            control_port = int(randomFreePort())
            tor_config.ControlPort = control_port
            config.tor.control_port = control_port

        if config.tor.socks_port:
            tor_config.SocksPort = config.tor.socks_port
        else:
            socks_port = int(randomFreePort())
            tor_config.SocksPort = socks_port
            config.tor.socks_port = socks_port

        if config.tor.data_dir:
            data_dir = os.path.expanduser(config.tor.data_dir)

            if not os.path.exists(data_dir):
                log.msg("%s does not exist. Creating it." % data_dir)
                os.makedirs(data_dir)
            tor_config.DataDirectory = data_dir

        tor_config.save()

        log.debug("Setting control port as %s" % tor_config.ControlPort)
        log.debug("Setting SOCKS port as %s" % tor_config.SocksPort)

        d = launch_tor(tor_config, reactor,
                tor_binary=config.advanced.tor_binary,
                progress_updates=updates)
        d.addCallback(setup_complete)
        d.addErrback(setup_failed)
        return d

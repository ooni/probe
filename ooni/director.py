import os

from twisted.internet import defer
from twisted.python.failure import Failure

from ooni.managers import ReportEntryManager, MeasurementManager
from ooni.reporter import Report
from ooni.utils import log, generate_filename
from ooni.nettest import NetTest, getNetTestInformation
from ooni.settings import config
from ooni.nettest import normalizeTestName
from ooni.deck.store import input_store, deck_store
from ooni.geoip import probe_ip

from ooni.agent.scheduler import run_system_tasks
from ooni.utils.onion import start_tor, connect_to_control_port, get_tor_config

class DirectorEvent(object):
    def __init__(self, type="update", message=""):
        self.type = type
        self.message = message


class Director(object):
    """
    Singleton object responsible for coordinating the Measurements Manager
    and the Reporting Manager.

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
    # Only list NetTests belonging to these categories
    categories = ['blocking', 'manipulation', 'third_party']

    def __init__(self):
        self.activeNetTests = []

        self.measurementManager = MeasurementManager()
        self.measurementManager.director = self

        self.reportEntryManager = ReportEntryManager()
        self.reportEntryManager.director = self
        # Link the TaskManager's by least available slots.
        self.measurementManager.child = self.reportEntryManager
        # Notify the parent when tasks complete # XXX deadlock!?
        self.reportEntryManager.parent = self.measurementManager

        self.successfulMeasurements = 0
        self.failedMeasurements = 0

        self.totalMeasurements = 0

        # The cumulative runtime of all the measurements
        self.totalMeasurementRuntime = 0

        self.failures = []

        # This deferred is fired once all the measurements and their reporting
        # tasks are completed.
        self.allTestsDone = defer.Deferred()
        self.sniffers = {}

        self.input_store = input_store
        self.deck_store = deck_store

        self._reset_director_state()
        self._reset_tor_state()

        self._subscribers = []

    def subscribe(self, handler):
        self._subscribers.append(handler)

    def unsubscribe(self, handler):
        self._subscribers.remove(handler)

    def notify(self, event):
        for handler in self._subscribers:
            try:
                handler(event)
            except Exception as exc:
                log.err("Failed to run handler")
                log.exception(exc)

    def _reset_director_state(self):
        self._director_state = 'not-running'
        self._director_starting = defer.Deferred()
        self._director_starting.addErrback(self._director_startup_failure)
        self._director_starting.addCallback(self._director_startup_success)

    def _director_startup_failure(self, failure):
        self._reset_director_state()
        self.notify(DirectorEvent("error",
                                  "Failed to start the director"))
        return failure

    def _director_startup_success(self, result):
        self._director_state = 'running'
        self.notify(DirectorEvent("success",
                                  "Successfully started the director"))
        return result

    def _reset_tor_state(self):
        # This can be either 'not-running', 'starting' or 'running'
        self._tor_state = 'not-running'
        self._tor_starting = defer.Deferred()
        self._tor_starting.addErrback(self._tor_startup_failure)
        self._tor_starting.addCallback(self._tor_startup_success)

    def _tor_startup_failure(self, failure):
        log.err("Failed to start tor")
        log.exception(failure)
        self._reset_tor_state()
        self.notify(DirectorEvent("error",
                                  "Failed to start Tor"))
        return failure

    def _tor_startup_success(self, result):
        log.msg("Tor has started")
        self._tor_state = 'running'
        self.notify(DirectorEvent("success",
                                  "Successfully started Tor"))
        return result

    def getNetTests(self):
        nettests = {}

        def is_nettest(filename):
            return not filename == '__init__.py' and filename.endswith('.py')

        for category in self.categories:
            dirname = os.path.join(config.nettest_directory, category)
            # print path to all filenames.
            for filename in os.listdir(dirname):
                if is_nettest(filename):
                    net_test_file = os.path.join(dirname, filename)
                    try:
                        nettest = getNetTestInformation(net_test_file)
                    except:
                        log.err("Error processing %s" % filename)
                        continue
                    nettest['category'] = category.replace('/', '')

                    if nettest['id'] in nettests:
                        log.err("Found a two tests with the same name %s, %s" %
                                (net_test_file,
                                 nettests[nettest['id']]['path']))
                    else:
                        category = dirname.replace(config.nettest_directory,
                                                   '')
                        nettests[nettest['id']] = nettest

        return nettests

    @defer.inlineCallbacks
    def _start(self, start_tor, check_incoherences, create_input_store):
        self.netTests = self.getNetTests()

        if start_tor:
            yield self.start_tor(check_incoherences)

        no_geoip = config.global_options.get('no-geoip', False)
        if no_geoip:
            aux = [False]
            if config.global_options.get('annotations') is not None:
                annotations = [k.lower() for k in config.global_options['annotations'].keys()]
                aux = map(lambda x: x in annotations, ["city", "country", "asn"])
            if not all(aux):
                log.msg("You should add annotations for the country, city and ASN")
        else:
            yield probe_ip.lookup()
            self.notify(DirectorEvent("success", "Looked up probe IP"))

        self.notify(DirectorEvent("success", "Running system tasks"))
        yield run_system_tasks(no_input_store=not create_input_store)
        self.notify(DirectorEvent("success", "Ran system tasks"))

    @defer.inlineCallbacks
    def start(self, start_tor=False, check_incoherences=True,
              create_input_store=True):
        self._director_state = 'starting'
        try:
            yield self._start(start_tor, check_incoherences, create_input_store)
            self._director_starting.callback(self._director_state)
        except Exception as exc:
            self._director_starting.errback(Failure(exc))
            raise

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

    def measurementSucceeded(self, result, measurement):
        log.debug("Successfully completed measurement: %s" % measurement)
        self.totalMeasurementRuntime += measurement.runtime
        self.successfulMeasurements += 1
        measurement.result = result
        test_name = normalizeTestName(measurement.testInstance.name)
        if test_name in self.sniffers:
            sniffer = self.sniffers[test_name]
            config.scapyFactory.unRegisterProtocol(sniffer)
            sniffer.close()
            del self.sniffers[test_name]
        return measurement

    def measurementFailed(self, failure, measurement):
        log.debug("Failed doing measurement: %s" % measurement)
        self.totalMeasurementRuntime += measurement.runtime

        self.failedMeasurements += 1
        measurement.result = failure
        return measurement

    def netTestDone(self, net_test):
        self.notify(DirectorEvent("success",
                                  "Successfully ran test {0}".format(
                                      net_test.testDetails['test_name'])))
        self.activeNetTests.remove(net_test)
        if len(self.activeNetTests) == 0:
            self.allTestsDone.callback(None)

    @defer.inlineCallbacks
    def start_net_test_loader(self, net_test_loader, report_filename,
                              collector_client=None, no_yamloo=False,
                              test_details=None, measurement_id=None):
        """
        Create the Report for the NetTest and start the report NetTest.

        Args:
            net_test_loader:
                an instance of :class:ooni.nettest.NetTestLoader
        """
        if test_details is None:
            test_details = net_test_loader.getTestDetails()
        test_cases = net_test_loader.getTestCases()

        if self.allTestsDone.called:
            self.allTestsDone = defer.Deferred()

        if config.privacy.includepcap or config.global_options.get('pcapfile', None):
            self.start_sniffing(test_details)
        report = Report(test_details, report_filename,
                        self.reportEntryManager,
                        collector_client,
                        no_yamloo,
                        measurement_id)

        yield report.open()
        net_test = NetTest(test_cases, test_details, report)
        net_test.director = self

        yield net_test.initialize()
        try:
            self.activeNetTests.append(net_test)
            self.measurementManager.schedule(net_test.generateMeasurements())

            yield net_test.done
            yield report.close()
        finally:
            self.netTestDone(net_test)

    def start_sniffing(self, test_details):
        """ Start sniffing with Scapy. Exits if required privileges (root) are not
        available.
        """
        from ooni.utils.txscapy import ScapySniffer, ScapyFactory

        if config.scapyFactory is None:
            config.scapyFactory = ScapyFactory(config.advanced.interface)

        # XXX this is dumb option to have in the ooniprobe.conf. Drop it in
        # the future.
        prefix = config.reports.pcap
        if prefix is None:
            prefix = 'report'

        filename_pcap = config.global_options.get('pcapfile', None)
        if filename_pcap is None:
            filename_pcap = generate_filename(test_details,
                                              prefix=prefix,
                                              extension='pcap')
        if len(self.sniffers) > 0:
            pcap_filenames = set(sniffer.pcapwriter.filename for sniffer in self.sniffers.values())
            pcap_filenames.add(filename_pcap)
            log.msg("pcap files %s can be messed up because several netTests are being executed in parallel." %
                    ','.join(pcap_filenames))

        sniffer = ScapySniffer(filename_pcap)
        self.sniffers[test_details['test_name']] = sniffer
        config.scapyFactory.registerProtocol(sniffer)
        log.msg("Starting packet capture to: %s" % filename_pcap)


    @defer.inlineCallbacks
    def start_tor(self, check_incoherences=False):
        """ Starts Tor
        Launches a Tor with :param: socks_port :param: control_port
        :param: tor_binary set in ooniprobe.conf
        """
        if self._tor_state == 'running':
            log.debug("Tor is already running")
            defer.returnValue(self._tor_state)
        elif self._tor_state == 'starting':
            log.debug("Tor is starting")
            yield self._tor_starting
            defer.returnValue(self._tor_state)

        log.msg("Starting Tor")
        self._tor_state = 'starting'
        if check_incoherences:
            try:
                yield config.check_tor()
            except Exception as exc:
                self._tor_starting.errback(Failure(exc))
                raise exc

        if config.advanced.start_tor and config.tor_state is None:
            tor_config = get_tor_config()

            try:
                yield start_tor(tor_config)
                self._tor_starting.callback(self._tor_state)
            except Exception as exc:
                log.err("Failed to start tor")
                log.exception(exc)
                self._tor_starting.errback(Failure(exc))

        elif config.tor.control_port and config.tor_state is None:
            try:
                yield connect_to_control_port()
                self._tor_starting.callback(self._tor_state)
            except Exception as exc:
                self._tor_starting.errback(Failure(exc))
        else:
            # This happens when we require tor to not be started and the
            # socks port is set.
            self._tor_starting.callback(self._tor_state)

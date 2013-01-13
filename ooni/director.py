from ooni.managers import ReportEntryManager, MeasurementManager
from ooni.reporter import Report

from ooni.nettest import NetTest

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

    def __init__(self, reporters):
        self.reporters = reporters

        self.netTests = []

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

    @property
    def measurementSuccessRatio(self):
        return self.successfulMeasurements / self.totalMeasurements

    @property
    def measurementFailureRatio(self):
        return self.failedMeasurements / self.totalMeasurements

    @property
    def measurementSuccessRate(self):
        """
        The speed at which tests are succeeding globally.

        This means that fast tests that perform a lot of measurements will
        impact this value quite heavily.
        """
        return self.successfulMeasurements / self.totalMeasurementRuntime

    @property
    def measurementFailureRate(self):
        """
        The speed at which tests are failing globally.
        """
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
        self.totalMeasurementRuntime += measurement.runtime

        self.successfulMeasurements += 1

    def measurementFailed(self, failure, measurement):
        self.totalMeasurementRuntime += measurement.runtime

        self.failedMeasurements += 1
        self.failures.append((failure, measurement))

    def startTest(self, net_test_file, options):
        """
        Create the Report for the NetTest and start the report NetTest.

        Args:
            net_test_file:
                is either a file path or a file like object that will be used to
                generate the test_cases.

            options:
                is a dict containing the options to be passed to the chosen net
                test.
        """
        report = Report(self.reporters)
        report.reportEntryManager = self.reportEntryManager

        net_test = NetTest(net_test_file, options, report)
        net_test.measurmentManager = self.measurementManager

        try:
            net_test.start()
        except Exception, e:
            pass


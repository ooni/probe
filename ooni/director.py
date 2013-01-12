from ooni.managers import ReportingEntryManager, MeasurementsManager
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

    def __init__(self):
        self.reporters = reporters

        self.netTests = []

        self.measurementsManager = MeasurementsManager(manager=self,
                netTests=self.netTests)
        self.measurementsManager.director = self

        self.reportEntryManager = ReportingEntryManager()
        self.reportEntryManager.director = self

    def startTest(self, net_test_file, inputs, options):
        """
        Create the Report for the NetTest and start the report NetTest.
        """
        report = Report()
        report.reportEntryManager = self.reportEntryManager

        net_test = NetTest(net_test_file, inputs, options, report)
        net_test.director = self

        self.measurementsManager.schedule(net_test.generateMeasurements())

    def measurementTimedOut(self, measurement):
        """
        This gets called every time a measurement times out independenty from
        the fact that it gets re-scheduled or not.
        """
        pass

    def measurementFailed(self, failure, measurement):
        pass

    def writeFailure(self, measurement, failure):
        pass

    def writeReport(self, report_write_task):
        self.reportingManager.write(report_write_task)


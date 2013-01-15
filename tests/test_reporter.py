from twisted.internet import defer
from twisted.trial import unittest

from ooni.reporter import Report, YAMLReporter, OONIBReporter
from ooni.managers import ReportEntryManager, TaskManager
from ooni.nettest import NetTest, NetTestState

from ooni.tasks import TaskWithTimeout
from tests.mocks import MockOReporter, MockTaskManager
from tests.mocks import MockMeasurement, MockNetTest

mockReportOptions = {'name':'foo_test', 'version': '0.1'}

class MockState(NetTestState):
    pass

class TestReport(unittest.TestCase):
    def setUp(self):
        self.taskManager = MockTaskManager()
        self.report = Report([MockOReporter], self.taskManager)
        self.state = MockState()

    def test_report_alltasksdone_callback_fires(self):
        for m in range(10):
            measurement = MockMeasurement(MockNetTest())
            self.report.write(measurement)

        @self.report.done.addCallback
        def done(reporters):
            self.assertEqual(len(reporters), 1)

        return self.report.done

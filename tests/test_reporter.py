from twisted.internet import defer
from twisted.trial import unittest

from ooni.reporter import Report, YAMLReporter, OONIBReporter
from ooni.managers import ReportEntryManager, TaskManager
from ooni.nettest import NetTest

from ooni.tasks import TaskMediator, TaskWithTimeout

mockReportOptions = {'name':'foo_test', 'version': '0.1'}

class MockOReporter(object):
    def __init__(self):
        self.created = defer.Deferred()

    def writeReportEntry(self, entry):
        pass

    def finish(self):
        pass

    def createReport(self):
        pass

class MockMeasurement(TaskWithTimeout):
    def __init__(self):
        TaskWithTimeout.__init__(self)

    def succeeded(self, result):
        pass

class MockTaskManager(TaskManager):
    def __init__(self):
        self.successes = []

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))

class TestReport(unittest.TestCase):
    def setUp(self):
        self.report = Report([MockOReporter])
        self.report.reportEntryManager = MockTaskManager()

    def test_report_alltasksdone_callback_fires(self):
        for m in range(10):
            measurement = MockMeasurement()
            self.report.write(measurement)

        self.report.report_mediator.allTasksScheduled()

        @self.report.done.addCallback
        def done(reporters):
            self.assertEqual(len(reporters), 1)

        return self.report.done

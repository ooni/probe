from twisted.internet import defer
from twisted.trial import unittest

from ooni.reporter import Report, YAMLReporter, OONIBReporter
from ooni.managers import ReportEntryManager, TaskManager
from ooni.nettest import NetTest, NetTestState

from ooni.tasks import TaskWithTimeout
from tests.mocks import MockOReporter, MockTaskManager
from tests.mocks import MockMeasurement, MockNetTest
from tests.mocks import MockOReporterThatFailsWrite
from tests.mocks import MockOReporterThatFailsWriteOnce
from tests.mocks import MockOReporterThatFailsOpen

from twisted.python import failure

class TestReport(unittest.TestCase):
    def setUp(self):
        pass
    def tearDown(self):
        pass
    def test_create_report_with_no_reporter(self):
        report = Report([],ReportEntryManager())
        self.assertIsInstance(report, Report)

    def test_create_report_with_single_reporter(self):
        report = Report([MockOReporter()], ReportEntryManager())
        self.assertIsInstance(report, Report)

    def test_create_report_with_multiple_reporters(self):
        report = Report([MockOReporter() for x in xrange(3)],
                ReportEntryManager())
        self.assertIsInstance(report, Report)

    def test_report_open_with_single_reporter(self):
        report = Report([MockOReporter()],ReportEntryManager())
        d = report.open()
        return d

    def test_report_open_with_multiple_reporter(self):
        report = Report([MockOReporter() for x in xrange(3)],
                ReportEntryManager())
        d = report.open()
        return d

    def test_fail_to_open_report_with_single_reporter(self):
        report = Report([MockOReporterThatFailsOpen()],
                ReportEntryManager())
        d = report.open()
        def f(x):
            self.assertEquals(len(report.reporters), 0)
        d.addCallback(f)
        return d

    def test_fail_to_open_single_report_with_multiple_reporter(self):
        report = Report([MockOReporterThatFailsOpen(), MockOReporter(),
                MockOReporter()], ReportEntryManager())
        d = report.open()
        def f(x):
            self.assertEquals(len(report.reporters),2)
        d.addCallback(f)
        return d

    def test_fail_to_open_all_reports_with_multiple_reporter(self):
        report = Report([MockOReporterThatFailsOpen() for x in xrange(3)],
                ReportEntryManager())
        d = report.open()
        def f(x):
            self.assertEquals(len(report.reporters),0)
        d.addCallback(f)
        return d

    def test_write_report_with_single_reporter_and_succeed(self):
        #XXX: verify that the MockOReporter writeReportEntry succeeds
        report = Report([MockOReporter()], ReportEntryManager())
        report.open()
        d = report.write(MockMeasurement(MockNetTest()))
        return d

    def test_write_report_with_single_reporter_and_fail_after_timeout(self):
        report = Report([MockOReporterThatFailsWrite()], ReportEntryManager())
        report.open()
        d = report.write(MockMeasurement(MockNetTest()))
        def f(err):
            self.assertEquals(len(report.reporters),0)
        d.addBoth(f)
        return d

    def test_write_report_with_single_reporter_and_succeed_after_timeout(self):
        report = Report([MockOReporterThatFailsWriteOnce()], ReportEntryManager())
        report.open()
        d = report.write(MockMeasurement(MockNetTest()))
        return d

    def test_write_report_with_multiple_reporter_and_succeed(self):
        report = Report([MockOReporter() for x in xrange(3)], ReportEntryManager())
        report.open()
        d = report.write(MockMeasurement(MockNetTest()))
        return d

    def test_write_report_with_multiple_reporter_and_fail_a_single_reporter(self):
        report = Report([MockOReporter(), MockOReporter(), MockOReporterThatFailsWrite()], ReportEntryManager())
        d = report.open()

        self.assertEquals(len(report.reporters),3)
        d = report.write(MockMeasurement(MockNetTest()))

        def f(x):
            # one of the reporters should have been removed
            self.assertEquals(len(report.reporters), 2)
        d.addBoth(f)
        return d

    def test_write_report_with_multiple_reporter_and_fail_all_reporter(self):
        report = Report([MockOReporterThatFailsWrite() for x in xrange(3)], ReportEntryManager())
        report.open()
        d = report.write(MockMeasurement(MockNetTest()))
        def f(err):
            self.assertEquals(len(report.reporters),0)
        d.addErrback(f)
        return d

#class TestYAMLReporter(unittest.TestCase):
#    def setUp(self):
#        pass
#    def tearDown(self):
#        pass
#    def test_create_yaml_reporter(self):
#        raise NotImplementedError
#    def test_open_yaml_report_and_succeed(self):
#        raise NotImplementedError
#    def test_open_yaml_report_and_fail(self):
#        raise NotImplementedError
#    def test_write_yaml_report_entry(self):
#        raise NotImplementedError
#    def test_write_multiple_yaml_report_entry(self):
#        raise NotImplementedError
#    def test_close_yaml_report(self):
#        raise NotImplementedError
#    def test_write_yaml_report_after_close(self):
#        raise NotImplementedError
#    def test_write_yaml_report_before_open(self):
#        raise NotImplementedError
#    def test_close_yaml_report_after_task_complete(self):
#        raise NotImplementedError

#class TestOONIBReporter(unittest.TestCase):
#    def setUp(self):
#        pass
#    def tearDown(self):
#        pass
#    def test_create_oonib_reporter(self):
#        raise NotImplementedError
#    def test_open_oonib_report_and_succeed(self):
#        raise NotImplementedError
#    def test_open_oonib_report_and_fail(self):
#        raise NotImplementedError
#    def test_write_oonib_report_entry_and_succeed(self):
#        raise NotImplementedError
#    def test_write_oonib_report_entry_and_succeed_after_timeout(self):
#        raise NotImplementedError
#    def test_write_oonib_report_entry_and_fail_after_timeout(self):
#        raise NotImplementedError
#    def test_write_oonib_report_after_close(self):
#        raise NotImplementedError
#    def test_write_oonib_report_before_open(self):
#        raise NotImplementedError
#    def test_close_oonib_report_and_succeed(self):
#        raise NotImplementedError
#    def test_close_oonib_report_and_fail(self):
#        raise NotImplementedError

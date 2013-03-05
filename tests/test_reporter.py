from twisted.internet import defer
from twisted.trial import unittest

from ooni.reporter import Report, YAMLReporter, OONIBReporter, safe_dump
from ooni.managers import ReportEntryManager, TaskManager
from ooni.nettest import NetTest, NetTestState
from ooni.errors import ReportNotCreated, ReportAlreadyClosed

from ooni.tasks import TaskWithTimeout
from tests.mocks import MockOReporter, MockTaskManager
from tests.mocks import MockMeasurement, MockNetTest
from tests.mocks import MockOReporterThatFailsWrite
from tests.mocks import MockOReporterThatFailsWriteOnce
from tests.mocks import MockOReporterThatFailsOpen

from twisted.python import failure
import yaml

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

class TestYAMLReporter(unittest.TestCase):
    def setUp(self):
        self.testDetails = {'software_name': 'ooniprobe', 'options':
        {'pcapfile': None, 'help': 0, 'subargs': ['-f', 'alexa_10'], 'resume':
        0, 'parallelism': '10', 'no-default-reporter': 0, 'testdeck': None,
        'test': 'nettests/blocking/http_requests.py', 'logfile': None,
        'collector': None, 'reportfile': None}, 'test_version': '0.2.3',
        'software_version': '0.0.10', 'test_name': 'http_requests_test',
        'start_time': 1362054343.0, 'probe_asn': 'AS0', 'probe_ip':
        '127.0.0.1', 'probe_cc': 'US'}

    def tearDown(self):
        pass
    def test_create_yaml_reporter(self):
        self.assertIsInstance(YAMLReporter(self.testDetails),
                YAMLReporter)
        
    def test_open_yaml_report_and_succeed(self):
        r = YAMLReporter(self.testDetails)
        r.createReport()
        # verify that testDetails was written to report properly
        def f(r):
            r._stream.seek(0)
            details, = yaml.safe_load_all(r._stream)
            self.assertEqual(details, self.testDetails)
        r.created.addCallback(f)
        return r.created

    #def test_open_yaml_report_and_fail(self):
    #    #XXX: YAMLReporter does not handle failures of this type
    #    pass

    def test_write_yaml_report_entry(self):
        r = YAMLReporter(self.testDetails)
        r.createReport()

        report_entry = {'foo':'bar', 'bin':'baz'}
        r.writeReportEntry(report_entry)

        # verify that details and entry were written to report
        def f(r):
            r._stream.seek(0)
            report = yaml.safe_load_all(r._stream)
            details, entry  = report
            self.assertEqual(details, self.testDetails)
            self.assertEqual(entry, report_entry)
        r.created.addCallback(f)
        return r.created

    def test_write_multiple_yaml_report_entry(self):
        r = YAMLReporter(self.testDetails)
        r.createReport()
        def reportEntry():
            for x in xrange(10):
                yield {'foo':'bar', 'bin':'baz', 'item':x}
        for entry in reportEntry():
            r.writeReportEntry(entry)
        # verify that details and multiple entries were written to report
        def f(r):
            r._stream.seek(0)
            report = yaml.safe_load_all(r._stream)
            details = report.next()
            self.assertEqual(details, self.testDetails)
            self.assertEqual([r for r in report], [r for r in reportEntry()])
        r.created.addCallback(f)
        return r.created

    def test_close_yaml_report(self):
        r = YAMLReporter(self.testDetails)
        r.createReport()
        r.finish()
        self.assertTrue(r._stream.closed)

    def test_write_yaml_report_after_close(self):
        r = YAMLReporter(self.testDetails)
        r.createReport()
        r.finish()
        def f(r):
            r.writeReportEntry("foo")
        r.created.addCallback(f)
        self.assertFailure(r.created, ReportAlreadyClosed)

    def test_write_yaml_report_before_open(self):
        r = YAMLReporter(self.testDetails)
        def f(r):
            r.writeReportEntry("foo")
        r.created.addCallback(f)
        self.assertFailure(r.created, ReportNotCreated)

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

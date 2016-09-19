from mock import patch, MagicMock

from twisted.internet import defer
from ooni.tests.bases import ConfigTestCase

mock_tor_check = MagicMock(return_value=True)

class TestOONIReport(ConfigTestCase):

    def _write_dummy_report(self, filename):
        from ooni.reporter import YAMLReporter
        from .test_reporter import test_details
        reporter = YAMLReporter(test_details, filename)
        reporter.createReport()
        reporter.writeReportEntry({"spam": "ham"})
        reporter.finish()

    def test_cli_status(self):
        mock_status = MagicMock()
        with patch('ooni.scripts.oonireport.status', mock_status):
            from ooni.scripts.oonireport import oonireport
            oonireport(_args=["status"])
            self.assertTrue(mock_status.called)

    @patch('ooni.scripts.oonireport.tor_check', mock_tor_check)
    def test_cli_upload(self):
        mock_upload = MagicMock()
        with patch('ooni.scripts.oonireport.upload', mock_upload):
            from ooni.scripts.oonireport import oonireport
            oonireport(_args=["upload", "dummy.yaml"])
            self.assertTrue(mock_upload.called)

    @patch('ooni.scripts.oonireport.tor_check', mock_tor_check)
    def test_cli_upload_all(self):
        mock_upload_all = MagicMock()
        with patch('ooni.scripts.oonireport.upload_all', mock_upload_all):
            from ooni.scripts.oonireport import oonireport
            oonireport(_args=["upload"])
            self.assertTrue(mock_upload_all.called)

    @patch('ooni.scripts.oonireport.CollectorClient')
    @patch('ooni.scripts.oonireport.OONIBReportLog')
    @patch('ooni.scripts.oonireport.OONIBReporter')
    def test_tool_upload(self, mock_oonib_reporter, mock_oonib_report_log,
                         mock_collector_client):

        mock_oonib_reporter_i = mock_oonib_reporter.return_value
        mock_oonib_reporter_i.createReport.return_value = defer.succeed("fake_id")
        mock_oonib_reporter_i.writeReportEntry.return_value = defer.succeed(True)
        mock_oonib_reporter_i.finish.return_value = defer.succeed(True)

        mock_oonib_report_log_i = mock_oonib_report_log.return_value
        mock_oonib_report_log_i.created.return_value = defer.succeed(True)
        mock_oonib_report_log_i.closed.return_value = defer.succeed(True)

        report_name = "dummy_report.yaml"
        self._write_dummy_report(report_name)
        from ooni.scripts import oonireport
        d = oonireport.upload(report_name, collector='httpo://thirteenchars123.onion')
        @d.addCallback
        def cb(result):
            mock_oonib_reporter_i.writeReportEntry.assert_called_with(
                {"spam": "ham"}
            )
        return d

    @patch('ooni.scripts.oonireport.CollectorClient')
    @patch('ooni.scripts.oonireport.OONIBReportLog')
    @patch('ooni.scripts.oonireport.OONIBReporter')
    def test_tool_upload_all(self, mock_oonib_reporter, mock_oonib_report_log,
                         mock_collector_client):

        mock_oonib_reporter_i = mock_oonib_reporter.return_value
        mock_oonib_reporter_i.createReport.return_value = defer.succeed("fake_id")
        mock_oonib_reporter_i.writeReportEntry.return_value = defer.succeed(True)
        mock_oonib_reporter_i.finish.return_value = defer.succeed(True)

        mock_oonib_report_log_i = mock_oonib_report_log.return_value
        mock_oonib_report_log_i.created.return_value = defer.succeed(True)
        mock_oonib_report_log_i.closed.return_value = defer.succeed(True)
        mock_oonib_report_log_i.get_to_upload.return_value = defer.succeed([("dummy_report.yaml", {'measurement_id': 'XX'})])

        report_name = "dummy_report.yaml"
        self._write_dummy_report(report_name)

        from ooni.scripts import oonireport
        d = oonireport.upload_all(collector='httpo://thirteenchars123.onion')
        @d.addCallback
        def cb(result):
            mock_oonib_reporter_i.writeReportEntry.assert_called_with(
                {"spam": "ham"}
            )
        return d

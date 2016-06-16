import yaml

from mock import patch, MagicMock

from twisted.internet import defer
from ooni.tests.bases import ConfigTestCase

from ooni.report import tool

mock_tor_check = MagicMock(return_value=True)

class TestOONIReport(ConfigTestCase):

    def _create_reporting_yaml(self, filename):
        from ooni.settings import config
        with open(config.report_log_file, 'w+') as f:
            yaml.dump({
                filename: {
                    "collector": "httpo://thirteenchars123.onion"
                }
            }, f)

    def _write_dummy_report(self, filename):
        from ooni.reporter import YAMLReporter
        from .test_reporter import test_details
        reporter = YAMLReporter(test_details, filename)
        reporter.createReport()
        reporter.writeReportEntry({"spam": "ham"})
        reporter.finish()

    def test_cli_status(self):
        mock_tool = MagicMock()
        with patch('ooni.report.cli.tool', mock_tool):
            from ooni.report import cli
            cli.run(["status"])
            self.assertTrue(mock_tool.status.called)

    @patch('ooni.report.cli.tor_check', mock_tor_check)
    def test_cli_upload(self):
        mock_tool = MagicMock()
        with patch('ooni.report.cli.tool', mock_tool):
            from ooni.report import cli
            cli.run(["upload", "dummy.yaml"])
            self.assertTrue(mock_tool.upload.called)

    @patch('ooni.report.cli.tor_check', mock_tor_check)
    def test_cli_upload_all(self):
        mock_tool = MagicMock()
        with patch('ooni.report.cli.tool', mock_tool):
            from ooni.report import cli
            cli.run(["upload"])
            self.assertTrue(mock_tool.upload_all.called)

    @patch('ooni.report.tool.CollectorClient')
    @patch('ooni.report.tool.OONIBReportLog')
    @patch('ooni.report.tool.OONIBReporter')
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
        self._create_reporting_yaml(report_name)
        self._write_dummy_report(report_name)

        d = tool.upload(report_name)
        @d.addCallback
        def cb(result):
            mock_oonib_reporter_i.writeReportEntry.assert_called_with(
                {"spam": "ham"}
            )
        return d

    @patch('ooni.report.tool.CollectorClient')
    @patch('ooni.report.tool.OONIBReportLog')
    @patch('ooni.report.tool.OONIBReporter')
    def test_tool_upload_all(self, mock_oonib_reporter, mock_oonib_report_log,
                         mock_collector_client):

        mock_oonib_reporter_i = mock_oonib_reporter.return_value
        mock_oonib_reporter_i.createReport.return_value = defer.succeed("fake_id")
        mock_oonib_reporter_i.writeReportEntry.return_value = defer.succeed(True)
        mock_oonib_reporter_i.finish.return_value = defer.succeed(True)

        mock_oonib_report_log_i = mock_oonib_report_log.return_value
        mock_oonib_report_log_i.created.return_value = defer.succeed(True)
        mock_oonib_report_log_i.closed.return_value = defer.succeed(True)
        mock_oonib_report_log_i.reports_to_upload = [("dummy_report.yaml", None)]

        report_name = "dummy_report.yaml"
        self._create_reporting_yaml(report_name)
        self._write_dummy_report(report_name)

        d = tool.upload_all()
        @d.addCallback
        def cb(result):
            mock_oonib_reporter_i.writeReportEntry.assert_called_with(
                {"spam": "ham"}
            )
        return d

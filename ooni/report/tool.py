import yaml

from twisted.internet import defer

from ooni.reporter import OONIBReporter, OONIBReportLog

from ooni.utils import log
from ooni.report import parser
from ooni.settings import config
from ooni.oonibclient import OONIBClient


@defer.inlineCallbacks
def upload(report_file, collector=None, bouncer=None):
    oonib_report_log = OONIBReportLog()

    print "Attempting to upload %s" % report_file

    with open(config.report_log_file) as f:
        report_log = yaml.safe_load(f)

    report = parser.ReportLoader(report_file)
    if bouncer and not collector:
        oonib_client = OONIBClient(bouncer)
        net_tests = [{
            'test-helpers': [],
            'input-hashes': report.header['input_hashes'],
            'name': report.header['test_name'],
            'version': report.header['test_version'],
        }]
        result = yield oonib_client.lookupTestCollector(
            net_tests
        )
        collector = str(result['net-tests'][0]['collector'])

    if collector is None:
        try:
            collector = report_log[report_file]['collector']
            if collector is None:
                raise KeyError
        except KeyError:
            raise Exception(
                "No collector or bouncer specified"
                " and collector not in report log."
            )

    oonib_reporter = OONIBReporter(report.header, collector)
    log.msg("Creating report for %s with %s" % (report_file, collector))
    report_id = yield oonib_reporter.createReport()
    yield oonib_report_log.created(report_file, collector, report_id)
    for entry in report:
        print "Writing entry"
        yield oonib_reporter.writeReportEntry(entry)
    log.msg("Closing report.")
    yield oonib_reporter.finish()
    yield oonib_report_log.closed(report_file)


@defer.inlineCallbacks
def upload_all(collector=None, bouncer=None):
    oonib_report_log = OONIBReportLog()

    for report_file, value in oonib_report_log.reports_to_upload:
        try:
            yield upload(report_file, collector, bouncer)
        except Exception as exc:
            log.exception(exc)


def print_report(report_file, value):
    print "* %s" % report_file
    print "  %s" % value['created_at']


def status():
    oonib_report_log = OONIBReportLog()

    print "Reports to be uploaded"
    print "----------------------"
    for report_file, value in oonib_report_log.reports_to_upload:
        print_report(report_file, value)

    print "Reports in progress"
    print "-------------------"
    for report_file, value in oonib_report_log.reports_in_progress:
        print_report(report_file, value)

    print "Incomplete reports"
    print "------------------"
    for report_file, value in oonib_report_log.reports_incomplete:
        print_report(report_file, value)

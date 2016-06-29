from __future__ import print_function
import yaml
import sys

from twisted.internet import defer

from ooni.constants import CANONICAL_BOUNCER_ONION
from ooni.reporter import OONIBReporter, OONIBReportLog

from ooni.utils import log
from ooni.report import parser
from ooni.settings import config
from ooni.backend_client import BouncerClient, CollectorClient

@defer.inlineCallbacks
def lookup_collector_client(report_header, bouncer):
    oonib_client = BouncerClient(bouncer)
    net_tests = [{
        'test-helpers': [],
        'input-hashes': report_header['input_hashes'],
        'name': report_header['test_name'],
        'version': report_header['test_version'],
    }]
    result = yield oonib_client.lookupTestCollector(
        net_tests
    )
    collector_client = CollectorClient(
        address=result['net-tests'][0]['collector']
    )
    defer.returnValue(collector_client)

@defer.inlineCallbacks
def upload(report_file, collector=None, bouncer=None):
    oonib_report_log = OONIBReportLog()
    collector_client = None
    if collector:
        collector_client = CollectorClient(address=collector)

    log.msg("Attempting to upload %s" % report_file)

    with open(config.report_log_file) as f:
        report_log = yaml.safe_load(f)

    report = parser.ReportLoader(report_file)
    if bouncer and collector_client is None:
        collector_client = yield lookup_collector_client(report.header,
                                                         bouncer)

    if collector_client is None:
        try:
            collector_settings = report_log[report_file]['collector']
            if collector_settings is None:
                log.msg("Skipping uploading of %s since this measurement "
                        "was run by specifying no collector." %
                        report_file)
                defer.returnValue(None)
            elif isinstance(collector_settings, dict):
                collector_client = CollectorClient(settings=collector_settings)
            elif isinstance(collector_settings, str):
                collector_client = CollectorClient(address=collector_settings)
        except KeyError:
            log.msg("Could not find %s in reporting.yaml. Looking up "
                    "collector with canonical bouncer." % report_file)
            collector_client = yield lookup_collector_client(report.header,
                                                             CANONICAL_BOUNCER_ONION)

    oonib_reporter = OONIBReporter(report.header, collector_client)
    log.msg("Creating report for %s with %s" % (report_file,
                                                collector_client.settings))
    report_id = yield oonib_reporter.createReport()
    report.header['report_id'] = report_id
    yield oonib_report_log.created(report_file,
                                   collector_client.settings,
                                   report_id)
    log.msg("Writing report entries")
    for entry in report:
        yield oonib_reporter.writeReportEntry(entry)
        sys.stdout.write('.')
        sys.stdout.flush()
    log.msg("Closing report")
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
    print("* %s" % report_file)
    print("  %s" % value['created_at'])


def status():
    oonib_report_log = OONIBReportLog()

    print("Reports to be uploaded")
    print("----------------------")
    for report_file, value in oonib_report_log.reports_to_upload:
        print_report(report_file, value)

    print("Reports in progress")
    print("-------------------")
    for report_file, value in oonib_report_log.reports_in_progress:
        print_report(report_file, value)

    print("Incomplete reports")
    print("------------------")
    for report_file, value in oonib_report_log.reports_incomplete:
        print_report(report_file, value)

from __future__ import print_function

import os
import sys
import yaml

from twisted.python import usage
from twisted.internet import defer, task

from ooni.constants import CANONICAL_BOUNCER_ONION
from ooni.reporter import OONIBReporter, OONIBReportLog

from ooni.utils import log
from ooni.settings import config
from ooni.backend_client import BouncerClient, CollectorClient

__version__ = "0.1.0"

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

    report = ReportLoader(report_file)
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

class ReportLoader(object):
    _header_keys = (
        'probe_asn',
        'probe_cc',
        'probe_ip',
        'start_time',
        'test_name',
        'test_version',
        'options',
        'input_hashes',
        'software_name',
        'software_version'
    )

    def __init__(self, report_filename):
        self._fp = open(report_filename)
        self._yfp = yaml.safe_load_all(self._fp)

        self.header = self._yfp.next()

    def __iter__(self):
        return self

    def next(self):
        try:
            return self._yfp.next()
        except StopIteration:
            self.close()
            raise StopIteration

    def close(self):
        self._fp.close()

class Options(usage.Options):

    synopsis = """%s [options] upload | status
""" % (os.path.basename(sys.argv[0]),)

    optFlags = [
        ["default-collector", "d", "Upload the reports to the default "
                                   "collector that is looked up with the "
                                   "canonical bouncer."]
    ]

    optParameters = [
        ["configfile", "f", None,
         "Specify the configuration file to use."],
        ["collector", "c", None,
         "Specify the collector to upload the result to."],
        ["bouncer", "b", None,
         "Specify the bouncer to query for a collector."]
    ]

    def opt_version(self):
        print("oonireport version: %s" % __version__)
        sys.exit(0)

    def parseArgs(self, *args):
        if len(args) == 0:
            raise usage.UsageError(
                "Must specify at least one command"
            )
            return
        self['command'] = args[0]
        if self['command'] not in ("upload", "status"):
            raise usage.UsageError(
                "Must specify either command upload or status"
            )
        if self['command'] == "upload":
            try:
                self['report_file'] = args[1]
            except IndexError:
                self['report_file'] = None


def tor_check():
    if not config.tor.socks_port:
        print("Currently oonireport requires that you start Tor yourself "
              "and set the socks_port inside of ooniprobe.conf")
        sys.exit(1)


def oonireport(reactor, args=sys.argv[1:]):
    options = Options()
    try:
        options.parseOptions(args)
    except Exception as exc:
        print("Error: %s" % exc)
        print(options)
        sys.exit(2)
    config.global_options = dict(options)
    config.set_paths()
    config.read_config_file()

    if options['default-collector']:
        options['bouncer'] = CANONICAL_BOUNCER_ONION

    if options['command'] == "upload" and options['report_file']:
        tor_check()
        return upload(options['report_file'],
                      options['collector'],
                      options['bouncer'])
    elif options['command'] == "upload":
        tor_check()
        return upload_all(options['collector'],
                          options['bouncer'])
    elif options['command'] == "status":
        return status()
    else:
        print(options)

def run():
    task.react(oonireport)

if __name__ == "__main__":
    run()

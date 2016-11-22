from __future__ import print_function

import os
import sys
import json
import yaml

from twisted.python import usage
from twisted.internet import defer, task, reactor

from ooni.constants import CANONICAL_BOUNCER_ONION
from ooni.reporter import OONIBReporter, OONIBReportLog

from ooni.utils import log
from ooni.settings import config
from ooni.backend_client import BouncerClient, CollectorClient
from ooni import __version__

@defer.inlineCallbacks
def lookup_collector_client(report_header, bouncer):
    oonib_client = BouncerClient(bouncer)
    net_tests = [{
        'test-helpers': [],
        'input-hashes': [],
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

class NoIDFound(Exception):
    pass

def report_path_to_id(report_file):
    measurement_dir = os.path.dirname(report_file)
    measurement_id = os.path.basename(measurement_dir)
    if os.path.dirname(measurement_dir) != config.measurements_directory:
        raise NoIDFound
    return measurement_id

@defer.inlineCallbacks
def upload(report_file, collector=None, bouncer=None, measurement_id=None):
    oonib_report_log = OONIBReportLog()
    collector_client = None
    if collector:
        collector_client = CollectorClient(address=collector)

    try:
        # Try to guess the measurement_id from the file path
        measurement_id = report_path_to_id(report_file)
    except NoIDFound:
        pass

    log.msg("Attempting to upload %s" % report_file)

    if report_file.endswith(".njson"):
        report = NJSONReportLoader(report_file)
    else:
        log.warn("Uploading of YAML formatted reports will be dropped in "
                 "future versions")
        report = YAMLReportLoader(report_file)

    if bouncer and collector_client is None:
        collector_client = yield lookup_collector_client(report.header,
                                                         bouncer)

    if collector_client is None:
        if measurement_id:
            report_log = yield oonib_report_log.get_report_log(measurement_id)
            collector_settings = report_log['collector']
            print(collector_settings)
            if collector_settings is None or len(collector_settings) == 0:
                log.warn("Skipping uploading of %s since this measurement "
                         "was run by specifying no collector." %
                          report_file)
                defer.returnValue(None)
            elif isinstance(collector_settings, dict):
                collector_client = CollectorClient(settings=collector_settings)
            elif isinstance(collector_settings, str):
                collector_client = CollectorClient(address=collector_settings)
        else:
            log.msg("Looking up collector with canonical bouncer." % report_file)
            collector_client = yield lookup_collector_client(report.header,
                                                             CANONICAL_BOUNCER_ONION)

    oonib_reporter = OONIBReporter(report.header, collector_client)
    log.msg("Creating report for %s with %s" % (report_file,
                                                collector_client.settings))
    report_id = yield oonib_reporter.createReport()
    report.header['report_id'] = report_id
    if measurement_id:
        log.debug("Marking it as created")
        yield oonib_report_log.created(measurement_id,
                                       collector_client.settings)
    log.msg("Writing report entries")
    for entry in report:
        yield oonib_reporter.writeReportEntry(entry)
        log.msg("Written entry")
    log.msg("Closing report")
    yield oonib_reporter.finish()
    if measurement_id:
        log.debug("Closing log")
        yield oonib_report_log.closed(measurement_id)


@defer.inlineCallbacks
def upload_all(collector=None, bouncer=None, upload_incomplete=False):
    oonib_report_log = OONIBReportLog()

    reports_to_upload = yield oonib_report_log.get_to_upload()
    for report_file, value in reports_to_upload:
        try:
            yield upload(report_file, collector, bouncer,
                         value['measurement_id'])
        except Exception as exc:
            log.exception(exc)

    if upload_incomplete:
        reports_to_upload = yield oonib_report_log.get_incomplete()
        for report_file, value in reports_to_upload:
            try:
                yield upload(report_file, collector, bouncer,
                             value['measurement_id'])
            except Exception as exc:
                log.exception(exc)

def print_report(report_file, value):
    print("* %s" % report_file)
    print("  %s" % value['last_update'])


@defer.inlineCallbacks
def status():
    oonib_report_log = OONIBReportLog()

    reports_to_upload = yield oonib_report_log.get_to_upload()
    print("Reports to be uploaded")
    print("----------------------")
    for report_file, value in reports_to_upload:
        print_report(report_file, value)

    reports_in_progress = yield oonib_report_log.get_in_progress()
    print("Reports in progress")
    print("-------------------")
    for report_file, value in reports_in_progress:
        print_report(report_file, value)

    reports_incomplete = yield oonib_report_log.get_incomplete()
    print("Incomplete reports")
    print("------------------")
    for report_file, value in reports_incomplete:
        print_report(report_file, value)

class ReportLoader(object):
    _header_keys = (
        'probe_asn',
        'probe_cc',
        'probe_ip',
        'probe_city',
        'test_start_time',
        'test_name',
        'test_version',
        'options',
        'input_hashes',
        'software_name',
        'software_version',
        'data_format_version',
        'report_id',
        'test_helpers',
        'annotations',
        'id'
    )

    def __iter__(self):
        return self

    def close(self):
        self._fp.close()

class YAMLReportLoader(ReportLoader):
    def __init__(self, report_filename):
        self._fp = open(report_filename)
        self._yfp = yaml.safe_load_all(self._fp)

        self.header = self._yfp.next()

    def next(self):
        try:
            return self._yfp.next()
        except StopIteration:
            self.close()
            raise StopIteration

class NJSONReportLoader(ReportLoader):
    def __init__(self, report_filename):
        self._fp = open(report_filename)
        self.header = self._peek_header()

    def _peek_header(self):
        header = {}
        first_entry = json.loads(next(self._fp))
        for key in self._header_keys:
            header[key] = first_entry.get(key, None)
        self._fp.seek(0)
        return header

    def next(self):
        try:
            entry = json.loads(next(self._fp))
            for key in self._header_keys:
                entry.pop(key, None)
            test_keys = entry.pop('test_keys')
            entry.update(test_keys)
            return entry
        except StopIteration:
            self.close()
            raise StopIteration

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
        log.err("Currently oonireport requires that you start Tor yourself "
                "and set the socks_port inside of ooniprobe.conf")
        sys.exit(1)


def oonireport(_reactor=reactor, _args=sys.argv[1:]):
    options = Options()
    try:
        options.parseOptions(_args)
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
        log.start()
        tor_check()
        return upload(options['report_file'],
                      options['collector'],
                      options['bouncer'])
    elif options['command'] == "upload":
        log.start()
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

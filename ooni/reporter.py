import uuid
import yaml
import json
import os

from copy import deepcopy

from datetime import datetime

from yaml.representer import SafeRepresenter
from yaml.emitter import Emitter
from yaml.serializer import Serializer
from yaml.resolver import Resolver

from twisted.python.filepath import FilePath
from twisted.python.util import untilConcludes
from twisted.internet import defer
from twisted.internet.error import ConnectionRefusedError

from ooni.utils import log, is_process_running
from ooni.tasks import Measurement
try:
    from scapy.packet import Packet
except ImportError:
    log.err("Scapy is not installed.")

    class Packet(object):
        pass

from ooni import errors

from ooni import otime
from ooni.utils import generate_filename

from ooni.settings import config

from ooni.tasks import ReportEntry
from ooni.measurements import list_measurements


def createPacketReport(packet_list):
    """
    Takes as input a packet a list.

    Returns a dict containing a dict with the packet
    summary and the raw packet.
    """
    report = []
    for packet in packet_list:
        report.append({'raw_packet': str(packet),
                       'summary': str([packet])})
    return report


class OSafeRepresenter(SafeRepresenter):

    """
    This is a custom YAML representer that allows us to represent reports
    safely.
    It extends the SafeRepresenter to be able to also represent complex
    numbers and scapy packet.
    """

    def represent_data(self, data):
        """
        This is very hackish. There is for sure a better way either by using
        the add_multi_representer or add_representer, the issue though lies in
        the fact that Scapy packets are metaclasses that leads to
        yaml.representer.get_classobj_bases to not be able to properly get the
        base of class of a Scapy packet.
        XXX fully debug this problem
        """
        if isinstance(data, Packet):
            data = createPacketReport(data)
        return SafeRepresenter.represent_data(self, data)

    def represent_complex(self, data):
        if data.imag == 0.0:
            data = u'%r' % data.real
        elif data.real == 0.0:
            data = u'%rj' % data.imag
        elif data.imag > 0:
            data = u'%r+%rj' % (data.real, data.imag)
        else:
            data = u'%r%rj' % (data.real, data.imag)
        return self.represent_scalar(u'tag:yaml.org,2002:python/complex', data)

OSafeRepresenter.add_representer(complex,
                                 OSafeRepresenter.represent_complex)


class OSafeDumper(Emitter, Serializer, OSafeRepresenter, Resolver):

    """
    This is a modification of the YAML Safe Dumper to use our own Safe
    Representer that supports complex numbers.
    """

    def __init__(self, stream,
                 default_style=None, default_flow_style=None,
                 canonical=None, indent=None, width=None,
                 allow_unicode=None, line_break=None,
                 encoding=None, explicit_start=None, explicit_end=None,
                 version=None, tags=None):

        Emitter.__init__(self, stream, canonical=canonical,
                         indent=indent, width=width,
                         allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                            explicit_start=explicit_start,
                            explicit_end=explicit_end,
                            version=version, tags=tags)
        OSafeRepresenter.__init__(self, default_style=default_style,
                                  default_flow_style=default_flow_style)
        Resolver.__init__(self)


def safe_dump(data, stream=None, **kw):
    """
    Safely dump to a yaml file the specified data.
    """
    return yaml.dump_all([data], stream, Dumper=OSafeDumper, **kw)


class OReporter(object):

    def __init__(self, test_details):
        self.testDetails = test_details

    def createReport(self):
        """
        Override this with your own logic to implement tests.
        """
        raise NotImplemented

    def writeReportEntry(self, entry):
        """
        Takes as input an entry and writes a report for it.
        """
        raise NotImplemented

    def finish(self):
        pass


class YAMLReporter(OReporter):

    """
    These are useful functions for reporting to YAML format.

    report_destination:
        the destination directory of the report

    """

    def __init__(self, test_details, report_filename):
        self.report_path = report_filename
        OReporter.__init__(self, test_details)

    def _writeln(self, line):
        self._write("%s\n" % line)

    def _write(self, format_string, *args):
        if not self._stream:
            raise errors.ReportNotCreated
        if self._stream.closed:
            raise errors.ReportAlreadyClosed
        s = str(format_string)
        assert isinstance(s, type(''))
        if args:
            self._stream.write(s % args)
        else:
            self._stream.write(s)
        untilConcludes(self._stream.flush)

    def writeReportEntry(self, entry):
        log.debug("Writing report with YAML reporter")
        content = '---\n'
        if isinstance(entry, Measurement):
            report_entry = deepcopy(entry.testInstance.report)
        elif isinstance(entry, dict):
            report_entry = deepcopy(entry)
        else:
            raise Exception("Failed to serialise entry")
        content += safe_dump(report_entry)
        content += '...\n'
        self._write(content)

    def createReport(self):
        """
        Writes the report header and fire callbacks on self.created
        """
        log.debug("Creating %s" % self.report_path)
        self._stream = open(self.report_path, 'w+')

        self._writeln("###########################################")

        self._writeln("# OONI Probe Report for %s (%s)" % (
            self.testDetails['test_name'],
            self.testDetails['test_version'])
        )

        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

        self.writeReportEntry(self.testDetails)

    def finish(self):
        self._stream.close()

class NJSONReporter(OReporter):

    """
    report_destination:
        the destination directory of the report

    """

    def __init__(self, test_details, report_filename):
        self.report_path = report_filename
        OReporter.__init__(self, test_details)

    def _writeln(self, line):
        self._write(line)
        self._write("\n")

    def _write(self, data):
        if not self._stream:
            raise errors.ReportNotCreated
        if self._stream.closed:
            raise errors.ReportAlreadyClosed
        s = str(data)
        assert isinstance(s, type(''))
        self._stream.write(s)
        untilConcludes(self._stream.flush)

    def writeReportEntry(self, entry):
        if isinstance(entry, Measurement):
            e = deepcopy(entry.testInstance.report)
        elif isinstance(entry, dict):
            e = deepcopy(entry)
        else:
            raise Exception("Failed to serialise entry")
        report_entry = {
            'input': e.pop('input', None),
            'id': str(uuid.uuid4()),
            'test_start_time': e.pop('test_start_time', None),
            'measurement_start_time': e.pop('measurement_start_time', None),
            'test_runtime': e.pop('test_runtime', None),
            'test_keys': e
        }
        report_entry.update(self.testDetails)
        self._writeln(json.dumps(report_entry))

    def createReport(self):
        self._stream = open(self.report_path, 'w+')

    def finish(self):
        self._stream.close()


class OONIBReporter(OReporter):

    def __init__(self, test_details, collector_client):
        self.collector_client = collector_client

        self.reportId = None
        self.supportedFormats = ["yaml"]
        OReporter.__init__(self, test_details)

    def serializeEntry(self, entry, serialisation_format="yaml"):
        if serialisation_format == "json":
            if isinstance(entry, Measurement):
                e = deepcopy(entry.testInstance.report)

            elif isinstance(entry, dict):
                e = deepcopy(entry)
            else:
                raise Exception("Failed to serialise entry")
            report_entry = {
                'input': e.pop('input', None),
                'id': str(uuid.uuid4()),
                'test_start_time': e.pop('test_start_time', None),
                'measurement_start_time': e.pop('measurement_start_time', None),
                'test_runtime': e.pop('test_runtime', None),
                'test_keys': e
            }
            report_entry.update(self.testDetails)
            return report_entry
        else:
            content = '---\n'
            if isinstance(entry, Measurement):
                report_entry = entry.testInstance.report
            elif isinstance(entry, dict):
                report_entry = entry
            else:
                raise Exception("Failed to serialise entry")
            content += safe_dump(report_entry)
            content += '...\n'
            return content

    @defer.inlineCallbacks
    def writeReportEntry(self, entry):
        if "json" in self.supportedFormats:
            serialization_format = 'json'
        else:
            serialization_format = 'yaml'

        log.debug("Updating report with id %s" % (self.reportId))
        entry_content = self.serializeEntry(entry, serialization_format)
        try:
            yield self.collector_client.updateReport(self.reportId,
                                                     serialization_format,
                                                     entry_content)
        except Exception as exc:
            log.err("Error in writing report entry")
            log.exception(exc)
            raise errors.OONIBReportUpdateError

    @defer.inlineCallbacks
    def createReport(self):
        """
        Creates a report on the oonib collector.
        """
        log.msg("Creating report with OONIB Reporter. Please be patient.")
        log.msg("This may take up to 1-2 minutes...")

        try:
            response = yield self.collector_client.createReport(
                                            self.testDetails
            )
        except ConnectionRefusedError:
            log.err("Connection to reporting backend failed "
                    "(ConnectionRefusedError)")
            raise errors.OONIBReportCreationError
        except errors.HostUnreachable:
            log.err("Host is not reachable (HostUnreachable error")
            raise errors.OONIBReportCreationError
        except (errors.OONIBInvalidInputHash,
                errors.OONIBInvalidNettestName):
            log.err("The specified input or nettests cannot be submitted to "
                    "this collector.")
            log.msg("Try running a different test or try reporting to a "
                    "different collector.")
            raise errors.OONIBReportCreationError
        except errors.OONIBError:
            log.err("Failed to connect to reporter backend")
            raise errors.OONIBReportCreationError
        except Exception as exc:
            log.err("Failed to connect to reporter backend")
            log.exception(exc)
            raise errors.OONIBReportCreationError

        self.reportId = response['report_id'].encode('ascii')
        self.backendVersion = response['backend_version']

        self.supportedFormats = response.get('supported_formats', ["yaml"])

        log.debug("Created report with id %s" % response['report_id'])
        defer.returnValue(response['report_id'])

    def finish(self):
        log.debug("Closing report with id %s" % self.reportId)
        return self.collector_client.closeReport(self.reportId)

class NoReportLog(Exception):
    pass

class OONIBReportLog(object):

    """
    Used to keep track of report creation on a collector backend.
    """
    _date_format = "%Y%m%dT%H:%M:%SZ"

    def __init__(self):
        self.measurement_dir = FilePath(config.measurements_directory)

    def _parse_log_entry(self, in_file, measurement_id):
        entry = json.load(in_file)
        entry['last_update'] = datetime.strptime(entry['last_update'],
                                                 self._date_format)
        entry['measurements_path'] = self.measurement_dir.child(
            measurement_id).child('measurements.njson').path
        entry['measurement_id'] = measurement_id
        return entry

    def _lock_for_report_log(self, measurement_id):
        lock_file = self.measurement_dir.child(measurement_id).child("report_log.lock")
        return defer.DeferredFilesystemLock(lock_file.path)

    def _get_report_log_file(self, measurement_id):
        report_log_file = self.measurement_dir.child(measurement_id).child("report_log.json")
        return report_log_file

    @defer.inlineCallbacks
    def get_report_log(self, measurement_id):
        lock = self._lock_for_report_log(measurement_id)
        yield lock.deferUntilLocked()

        report_log_file = self._get_report_log_file(measurement_id)
        if not report_log_file.exists():
            lock.unlock()
            raise NoReportLog

        with report_log_file.open('r') as in_file:
            entry = self._parse_log_entry(in_file, measurement_id)

        lock.unlock()

        defer.returnValue(entry)

    @defer.inlineCallbacks
    def get_report_log_entries(self):
        entries = []
        for measurement in list_measurements():
            try:
                entry = yield self.get_report_log(measurement['id'])
                entry['completed'] = measurement['completed']
                entries.append(entry)
            except NoReportLog:
                continue
        defer.returnValue(entries)

    @defer.inlineCallbacks
    def update_log(self, measurement_id, value):
        lock = self._lock_for_report_log(measurement_id)
        yield lock.deferUntilLocked()

        report_log_file = self._get_report_log_file(measurement_id)
        with report_log_file.open('w+') as out_file:
            entry = value
            entry['last_update'] = datetime.utcnow().strftime(self._date_format)
            json.dump(entry, out_file)

        lock.unlock()

    @defer.inlineCallbacks
    def remove_log(self, measurement_id):
        lock = self._lock_for_report_log(measurement_id)
        yield lock.deferUntilLocked()

        report_log_file = self._get_report_log_file(measurement_id)
        try:
            log.debug("Deleting log file")
            report_log_file.remove()
        except Exception as exc:
            log.exception(exc)

        lock.unlock()

    @defer.inlineCallbacks
    def get_incomplete(self):
        incomplete_reports = []
        all_entries = yield self.get_report_log_entries()
        for entry in all_entries[:]:
            # This means that the measurement itself is incomplete
            if entry['completed'] is False:
                continue
            if entry['status'] in ('created',):
                if not is_process_running(entry['pid']):
                    incomplete_reports.append(
                        (entry['measurements_path'], entry)
                    )
            elif entry['status'] in ('incomplete',):
                    incomplete_reports.append(
                        (entry['measurements_path'], entry)
                    )
        defer.returnValue(incomplete_reports)

    @defer.inlineCallbacks
    def get_in_progress(self):
        in_progress_reports = []
        all_entries = yield self.get_report_log_entries()
        for entry in all_entries[:]:
            if entry['status'] in ('created',):
                if is_process_running(entry['pid']):
                    in_progress_reports.append(
                        (entry['measurements_path'], entry)
                    )
        defer.returnValue(in_progress_reports)

    @defer.inlineCallbacks
    def get_to_upload(self):
        to_upload_reports = []
        all_entries = yield self.get_report_log_entries()
        for entry in all_entries[:]:
            # This means that the measurement itself is incomplete
            if entry['completed'] is False:
                continue
            if entry['status'] in ('creation-failed', 'not-created'):
                to_upload_reports.append(
                    (entry['measurements_path'], entry)
                )
        defer.returnValue(to_upload_reports)

    def _update_status(self, measurement_id, status, collector_settings={}):
        value = {
            'pid': os.getpid(),
            'status': status,
            'collector': collector_settings
        }
        return self.update_log(measurement_id, value)

    def not_created(self, measurement_id):
        return self._update_status(measurement_id, 'not-created')

    def created(self, measurement_id, collector_settings):
        return self._update_status(measurement_id, 'created',
                                   collector_settings)


    def creation_failed(self, measurement_id, collector_settings):
        return self._update_status(measurement_id, 'creation-failed',
                                   collector_settings)

    def incomplete(self, measurement_id, collector_settings):
        return self._update_status(measurement_id, 'incomplete',
                                   collector_settings)

    def closed(self, measurement_id):
        return self.remove_log(measurement_id)


class Report(object):
    reportId = None

    def __init__(self, test_details, report_filename,
                 reportEntryManager, collector_client=None,
                 no_njson=False, measurement_id=None):
        """
        This is an abstraction layer on top of all the configured reporters.

        It allows to lazily write to the reporters that are to be used.

        Args:

            test_details:
                A dictionary containing the test details.

            report_filename:
                The file path for the report to be written.

            reportEntryManager:
                an instance of :class:ooni.tasks.ReportEntryManager

            collector:
                The address of the oonib collector for this report.

            no_njson:
                If we should disable reporting to disk.
        """
        self.test_details = test_details
        self.collector_client = collector_client

        if report_filename is None:
            report_filename = self.generateReportFilename()
        self.report_filename = report_filename

        self.measurement_id = measurement_id
        self.report_log = OONIBReportLog()

        self.njson_reporter = None
        self.oonib_reporter = None
        self.no_njson = no_njson

        self.done = defer.Deferred()
        self.reportEntryManager = reportEntryManager

    def generateReportFilename(self):
        report_filename = generate_filename(self.test_details,
                                            prefix='report',
                                            extension='njson')
        report_path = os.path.join('.', report_filename)
        return os.path.abspath(report_path)

    def open_oonib_reporter(self):
        def creation_failed(failure):
            self.oonib_reporter = None
            if self.measurement_id:
                return self.report_log.creation_failed(self.measurement_id,
                                                       self.collector_client.settings)

        def created(report_id):
            if not self.oonib_reporter:
                return
            self.test_details['report_id'] = report_id
            if self.measurement_id:
                return self.report_log.created(self.measurement_id,
                                               self.collector_client.settings)

        d = self.oonib_reporter.createReport()
        d.addErrback(creation_failed)
        d.addCallback(created)
        return d

    @defer.inlineCallbacks
    def open(self):
        """
        This will create all the reports that need to be created and fires the
        created callback of the reporter whose report got created.
        """
        if self.collector_client:
            self.oonib_reporter = OONIBReporter(self.test_details,
                                                self.collector_client)
            yield self.open_oonib_reporter()

        if not self.no_njson:
            self.njson_reporter = NJSONReporter(self.test_details,
                                                self.report_filename)
            if not self.oonib_reporter and self.measurement_id:
                yield self.report_log.not_created(self.measurement_id)
            yield defer.maybeDeferred(self.njson_reporter.createReport)

        defer.returnValue(self.reportId)

    def write(self, measurement):
        """
        Will return a deferred that will fire once the report for the specified
        measurement have been written to all the reporters.

        Args:

            measurement:
                an instance of :class:ooni.tasks.Measurement

        Returns:
            a deferred that will fire once all the report entries have
            been written or errbacks when no more reporters
        """

        d = defer.Deferred()
        deferreds = []

        def njson_report_failed(failure):
            d.errback(failure)

        def oonib_report_failed(failure):
            if self.measurement_id:
                return self.report_log.incomplete(self.measurement_id,
                                                  self.collector_client.settings)

        def all_reports_written(_):
            if not d.called:
                d.callback(None)

        if self.njson_reporter:
            write_njson_report = ReportEntry(self.njson_reporter, measurement)
            self.reportEntryManager.schedule(write_njson_report)
            write_njson_report.done.addErrback(njson_report_failed)
            deferreds.append(write_njson_report.done)

        if self.oonib_reporter:
            write_oonib_report = ReportEntry(self.oonib_reporter, measurement)
            self.reportEntryManager.schedule(write_oonib_report)
            write_oonib_report.done.addErrback(oonib_report_failed)
            deferreds.append(write_oonib_report.done)

        dl = defer.DeferredList(deferreds)
        dl.addCallback(all_reports_written)

        return d

    def close(self):
        """
        Close the report by calling it's finish method.

        Returns:
            a :class:twisted.internet.defer.DeferredList that will fire when
            all the reports have been closed.

        """
        d = defer.Deferred()
        deferreds = []

        def njson_report_failed(failure):
            d.errback(failure)

        def oonib_report_closed(result):
            if self.measurement_id:
                return self.report_log.closed(self.measurement_id)

        def oonib_report_failed(result):
            log.exception(result)
            log.err("Failed to close oonib report.")

        def all_reports_closed(_):
            if not d.called:
                d.callback(None)

        if self.njson_reporter:
            close_njson = defer.maybeDeferred(self.njson_reporter.finish)
            close_njson.addErrback(njson_report_failed)
            deferreds.append(close_njson)

        if self.oonib_reporter:
            close_oonib = self.oonib_reporter.finish()
            close_oonib.addCallback(oonib_report_closed)
            close_oonib.addErrback(oonib_report_failed)
            deferreds.append(close_oonib)

        dl = defer.DeferredList(deferreds)
        dl.addCallback(all_reports_closed)

        return d

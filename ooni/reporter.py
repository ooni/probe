import traceback
import itertools
import logging
import time
import yaml
import json
import sys
import os
import re

from yaml.representer import *
from yaml.emitter import *
from yaml.serializer import *
from yaml.resolver import *
from twisted.python.util import untilConcludes
from twisted.trial import reporter
from twisted.internet import defer, reactor
from twisted.internet.error import ConnectionRefusedError
from twisted.python.failure import Failure

from ooni.utils import log

try:
    from scapy.packet import Packet
except ImportError:
    log.err("Scapy is not installed.")


from ooni import errors

from ooni import otime
from ooni.utils import pushFilenameStack
from ooni.utils.net import BodyReceiver, StringProducer, userAgents

from ooni.settings import config

from ooni.tasks import ReportEntry, TaskTimedOut, ReportTracker

class ReporterException(Exception):
    pass

def createPacketReport(packet_list):
    """
    Takes as input a packet a list.

    Returns a dict containing a dict with the packet
    summary and the raw packet.
    """
    report = []
    for packet in packet_list:
        report.append({'raw_packet': str(packet),
            'summary': str(packet.summary())})
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
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        OSafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

class NoTestIDSpecified(Exception):
    pass

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

    def testDone(self, test, test_name):
        # XXX put this inside of Report.close
        # or perhaps put something like this inside of netTestDone
        log.msg("Finished running %s" % test_name)
        test_report = dict(test.report)

        if isinstance(test.input, Packet):
            test_input = createPacketReport(test.input)
        else:
            test_input = test.input

        test_report['input'] = test_input
        test_report['test_name'] = test_name
        test_report['test_started'] = test._start_time
        test_report['test_runtime'] = time.time() - test._start_time

        return defer.maybeDeferred(self.writeReportEntry, test_report)

class InvalidDestination(ReporterException):
    pass

class YAMLReporter(OReporter):
    """
    These are useful functions for reporting to YAML format.

    report_destination:
        the destination directory of the report

    """
    def __init__(self, test_details, report_destination='.'):
        self.reportDestination = report_destination

        if not os.path.isdir(report_destination):
            raise InvalidDestination

        report_filename = "report-" + \
                test_details['test_name'] + "-" + \
                otime.timestamp() + ".yamloo"

        report_path = os.path.join(self.reportDestination, report_filename)

        if os.path.exists(report_path):
            log.msg("Report already exists with filename %s" % report_path)
            pushFilenameStack(report_path)

        self.report_path = report_path
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
        self._write('---\n')
        if isinstance(entry, Failure):
            self._write(entry.value)
        else:
            self._write(safe_dump(entry))
        self._write('...\n')

    def createReport(self):
        """
        Writes the report header and fire callbacks on self.created
        """
        log.debug("Creating %s" % self.report_path)
        self._stream = open(self.report_path, 'w+')

        self._writeln("###########################################")

        self._writeln("# OONI Probe Report for %s (%s)" % (self.testDetails['test_name'],
                    self.testDetails['test_version']))
        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

        self.writeReportEntry(self.testDetails)

    def finish(self):
        self._stream.close()

def collector_supported(collector_address):
    if collector_address.startswith('httpo') \
            and (not (config.tor_state or config.tor.socks_port)):
        return False
    return True

class OONIBReporter(OReporter):
    def __init__(self, test_details, collector_address):
        self.collectorAddress = collector_address
        self.validateCollectorAddress()

        self.reportID = None

        OReporter.__init__(self, test_details)

    def validateCollectorAddress(self):
        """
        Will raise :class:ooni.errors.InvalidOONIBCollectorAddress an exception
        if the oonib reporter is not valid.
        """
        regexp = '^(http|httpo):\/\/[a-zA-Z0-9\-\.]+(:\d+)?$'
        if not re.match(regexp, self.collectorAddress):
            raise errors.InvalidOONIBCollectorAddress

    @defer.inlineCallbacks
    def writeReportEntry(self, entry):
        log.debug("Writing report with OONIB reporter")
        content = '---\n'
        content += safe_dump(entry)
        content += '...\n'

        url = self.collectorAddress + '/report'

        request = {'report_id': self.reportID,
                'content': content}

        log.debug("Updating report with id %s (%s)" % (self.reportID, url))
        request_json = json.dumps(request)
        log.debug("Sending %s" % request_json)

        bodyProducer = StringProducer(json.dumps(request))

        try:
            response = yield self.agent.request("PUT", url,
                                bodyProducer=bodyProducer)
        except:
            # XXX we must trap this in the runner and make sure to report the
            # data later.
            log.err("Error in writing report entry")
            raise errors.OONIBReportUpdateError

    @defer.inlineCallbacks
    def createReport(self):
        """
        Creates a report on the oonib collector.
        """
        # XXX we should probably be setting this inside of the constructor,
        # however config.tor.socks_port is not set until Tor is started and the
        # reporter is instantiated before Tor is started. We probably want to
        # do this with some deferred kung foo or instantiate the reporter after
        # tor is started.

        from ooni.utils.txagentwithsocks import Agent
        from twisted.internet import reactor
        try:
            self.agent = Agent(reactor, sockshost="127.0.0.1",
                socksport=int(config.tor.socks_port))
        except Exception, e:
            log.exception(e)

        url = self.collectorAddress + '/report'

        content = '---\n'
        content += safe_dump(self.testDetails)
        content += '...\n'

        request = {'software_name': self.testDetails['software_name'],
            'software_version': self.testDetails['software_version'],
            'probe_asn': self.testDetails['probe_asn'],
            'test_name': self.testDetails['test_name'],
            'test_version': self.testDetails['test_version'],
            # XXX there is a bunch of redundancy in the arguments getting sent
            # to the backend. This may need to get changed in the client and the
            # backend.
            'content': content
        }

        log.msg("Reporting %s" % url)
        request_json = json.dumps(request)
        log.debug("Sending %s" % request_json)

        bodyProducer = StringProducer(json.dumps(request))

        log.msg("Creating report with OONIB Reporter. Please be patient.")
        log.msg("This may take up to 1-2 minutes...")

        try:
            response = yield self.agent.request("POST", url,
                                bodyProducer=bodyProducer)
        except ConnectionRefusedError:
            log.err("Connection to reporting backend failed (ConnectionRefusedError)")
            #yield defer.fail(OONIBReportCreationError())
            raise errors.OONIBReportCreationError

        except errors.HostUnreachable:
            log.err("Host is not reachable (HostUnreachable error")
            raise errors.OONIBReportCreationError

        except Exception, e:
            log.err("Failed to connect to reporter backend")
            log.exception(e)
            raise errors.OONIBReportCreationError

        # This is a little trix to allow us to unspool the response. We create
        # a deferred and call yield on it.
        response_body = defer.Deferred()
        response.deliverBody(BodyReceiver(response_body))

        backend_response = yield response_body

        try:
            parsed_response = json.loads(backend_response)
        except Exception, e:
            log.err("Failed to parse collector response")
            log.exception(e)
            raise errors.OONIBReportCreationError

        self.reportID = parsed_response['report_id']
        self.backendVersion = parsed_response['backend_version']
        log.debug("Created report with id %s" % parsed_response['report_id'])

    @defer.inlineCallbacks
    def finish(self):
        url = self.collectorAddress + '/report/' + self.reportID + '/close'
        log.debug("Closing the report %s" % url)
        response = yield self.agent.request("POST", str(url))

class ReportClosed(Exception):
    pass

class Report(object):
    def __init__(self, reporters, reportEntryManager):
        """
        This is an abstraction layer on top of all the configured reporters.

        It allows to lazily write to the reporters that are to be used.

        Args:

            reporters:
                a list of :class:ooni.reporter.OReporter instances

            reportEntryManager:
                an instance of :class:ooni.tasks.ReportEntryManager
        """
        self.reporters = reporters

        self.done = defer.Deferred()
        self.reportEntryManager = reportEntryManager

        self._reporters_openned = 0
        self._reporters_written = 0
        self._reporters_closed = 0

    def open(self):
        """
        This will create all the reports that need to be created and fires the
        created callback of the reporter whose report got created.
        """
        all_openned = defer.Deferred()

        def are_all_openned():
            if len(self.reporters) == self._reporters_openned:
                all_openned.callback(self._reporters_openned)

        for reporter in self.reporters[:]:

            def report_created(result):
                log.debug("Created report with %s" % reporter)
                self._reporters_openned += 1
                are_all_openned()

            def report_failed(failure):
                try:
                    self.failedOpeningReport(failure, reporter)
                except errors.NoMoreReporters, e:
                    all_openned.errback(defer.fail(e))
                else:
                    are_all_openned()
                return

            d = defer.maybeDeferred(reporter.createReport)
            d.addCallback(report_created)
            d.addErrback(report_failed)

        return all_openned

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
        all_written = defer.Deferred()
        report_tracker = ReportTracker(self.reporters)

        for reporter in self.reporters[:]:
            def report_completed(task):
                report_tracker.completed()
                if report_tracker.finished():
                    all_written.callback(report_tracker)

            report_entry_task = ReportEntry(reporter, measurement)
            self.reportEntryManager.schedule(report_entry_task)

            report_entry_task.done.addBoth(report_completed)

        return all_written

    def failedOpeningReport(self, failure, reporter):
        """
        This errback get's called every time we fail to create a report.
        By fail we mean that the number of retries has exceeded.
        Once a report has failed to be created with a reporter we give up and
        remove the reporter from the list of reporters to write to.
        """
        log.err("Failed to open %s reporter, giving up..." % reporter)
        log.err("Reporter %s failed, removing from report..." % reporter)
        #log.exception(failure)
        self.reporters.remove(reporter)
        # Don't forward the exception unless there are no more reporters
        if len(self.reporters) == 0:
            log.err("Removed last reporter %s" % reporter)
            raise errors.NoMoreReporters
        return

    def close(self):
        """
        Close the report by calling it's finish method.

        Returns:
            a :class:twisted.internet.defer.DeferredList that will fire when
            all the reports have been closed.

        """
        all_closed = defer.Deferred()

        for reporter in self.reporters[:]:
            def report_closed(result):
                self._reporters_closed += 1
                if len(self.reporters) == self._reporters_closed:
                    all_closed.callback(self._reporters_closed)

            def report_failed(failure):
                log.err("Failed closing report")
                log.exception(failure)

            d = defer.maybeDeferred(reporter.finish)
            d.addCallback(report_closed)
            d.addErrback(report_failed)

        return all_closed

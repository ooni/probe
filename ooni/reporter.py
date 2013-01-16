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

from ooni.utils import log

try:
    from scapy.packet import Packet
except ImportError:
    log.err("Scapy is not installed.")


from ooni import otime
from ooni.utils import geodata, pushFilenameStack
from ooni.utils.net import BodyReceiver, StringProducer, userAgents

from ooni import config

from ooni.tasks import ReportEntry

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
        self.created = defer.Deferred()
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

        test_started = test._start_time
        test_runtime = time.time() - test_started

        report = {'input': test_input,
                'test_name': test_name,
                'test_started': test_started,
                'test_runtime': test_runtime,
                'report': test_report}
        return defer.maybeDeferred(self.writeReportEntry, report)

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

        log.debug("Creating %s" % report_path)
        self._stream = open(report_path, 'w+')

        OReporter.__init__(self, test_details)

    def _writeln(self, line):
        self._write("%s\n" % line)

    def _write(self, format_string, *args):
        s = str(format_string)
        assert isinstance(s, type(''))
        if args:
            self._stream.write(s % args)
        else:
            self._stream.write(s)
        untilConcludes(self._stream.flush)

    def writeReportEntry(self, entry):
        #XXX: all _write, _writeln inside this call should be atomic
        log.debug("Writing report with YAML reporter")
        self._write('---\n')
        self._write(safe_dump(entry))
        self._write('...\n')

    def createReport(self):
        """
        Writes the report header and fire callbacks on self.created
        """
        self._writeln("###########################################")

        self._writeln("# OONI Probe Report for %s (%s)" % (self.testDetails['test_name'],
                    self.testDetails['test_version']))
        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

        self.writeReportEntry(self.testDetails)

    def finish(self):
        self._stream.close()

class OONIBReportError(Exception):
    pass

class OONIBReportUpdateError(OONIBReportError):
    pass

class OONIBReportCreationError(OONIBReportError):
    pass

class OONIBTestDetailsLookupError(OONIBReportError):
    pass

class OONIBReporter(OReporter):
    collector_address = ''
    def __init__(self, test_details, collector_address):
        self.collector_address = collector_address
        self.report_id = None

        from ooni.utils.txagentwithsocks import Agent
        from twisted.internet import reactor
        try:
            self.agent = Agent(reactor, sockshost="127.0.0.1",
                socksport=int(config.tor.socks_port))
        except Exception, e:
            log.exception(e)

        OReporter.__init__(self, test_details)

    @defer.inlineCallbacks
    def writeReportEntry(self, entry):
        log.debug("Writing report with OONIB reporter")
        content = '---\n'
        content += safe_dump(entry)
        content += '...\n'

        url = self.collector_address + '/report'

        request = {'report_id': self.report_id,
                'content': content}

        log.debug("Updating report with id %s (%s)" % (self.report_id, url))
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
            raise OONIBReportUpdateError

    @defer.inlineCallbacks
    def createReport(self, options):
        """
        Creates a report on the oonib collector.
        """
        url = self.collector_address + '/report'

        test_details['options'] = self.cmd_line_options

        log.debug("Obtained test_details: %s" % test_details)

        content = '---\n'
        content += safe_dump(test_details)
        content += '...\n'

        test_name = options['name']
        test_version = options['version']

        request = {'software_name': test_details['software_name'],
            'software_version': test_details['software_version'],
            'probe_asn': test_details['probe_asn'],
            'test_name': test_details['test_name'],
            'test_version': test_details['test_version'],
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
            raise OONIBReportCreationError

        except Exception, e:
            log.exception(e)
            raise OONIBReportCreationError

        # This is a little trix to allow us to unspool the response. We create
        # a deferred and call yield on it.
        response_body = defer.Deferred()
        response.deliverBody(BodyReceiver(response_body))

        backend_response = yield response_body

        try:
            parsed_response = json.loads(backend_response)
        except Exception, e:
            log.exception(e)
            raise OONIBReportCreationError

        self.report_id = parsed_response['report_id']
        self.backend_version = parsed_response['backend_version']
        log.debug("Created report with id %s" % parsed_response['report_id'])

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
        self.done.addCallback(self.close)

        self.reportEntryManager = reportEntryManager

    def open(self):
        """
        This will create all the reports that need to be created and fires the
        created callback of the reporter whose report got created.
        """
        for reporter in self.reporters:
            d = defer.maybeDeferred(reporter.createReport)
            d.addCallback(reporter.created.callback)

    def write(self, measurement):
        """
        This is a lazy call that will write to all the reporters by waiting on
        them to be created.

        Will return a deferred that will fire once the report for the specified
        measurement have been written to all the reporters.

        Args:

            measurement:
                an instance of :class:ooni.tasks.Measurement

        Returns:
            a deferred list that will fire once all the report entries have
            been written.
        """
        l = []
        for reporter in self.reporters:
            def writeReportEntry(result):
                report_write_task = ReportEntry(reporter, measurement)
                self.reportEntryManager.schedule(report_write_task)
                return report_write_task.done

            d = reporter.created.addBoth(writeReportEntry)
            l.append(d)

        dl = defer.DeferredList(l)
        return dl

    def close(self, _):
        """
        Close the report by calling it's finish method.

        Returns:
            a :class:twisted.internet.defer.DeferredList that will fire when
            all the reports have been closed.

        """
        l = []
        for reporter in self.reporters:
            d = defer.maybeDeferred(reporter.finish)
            l.append(d)
        dl = defer.DeferredList(l)
        return dl


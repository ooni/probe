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

def getTestDetails(options):
    from ooni import __version__ as software_version

    client_geodata = {}
    if config.probe_ip and (config.privacy.includeip or \
            config.privacy.includeasn or \
            config.privacy.includecountry or \
            config.privacy.includecity):
        log.msg("We will include some geo data in the report")
        client_geodata = geodata.IPToLocation(config.probe_ip)

    if config.privacy.includeip:
        client_geodata['ip'] = config.probe_ip
    else:
        client_geodata['ip'] = "127.0.0.1"

    # Here we unset all the client geodata if the option to not include then
    # has been specified
    if client_geodata and not config.privacy.includeasn:
        client_geodata['asn'] = 'AS0'
    elif 'asn' in client_geodata:
        # XXX this regexp should probably go inside of geodata
        client_geodata['asn'] = \
                re.search('AS\d+', client_geodata['asn']).group(0)
        log.msg("Your AS number is: %s" % client_geodata['asn'])
    else:
        client_geodata['asn'] = None

    if (client_geodata and not config.privacy.includecity) \
            or ('city' not in client_geodata):
        client_geodata['city'] = None

    if (client_geodata and not config.privacy.includecountry) \
            or ('countrycode' not in client_geodata):
        client_geodata['countrycode'] = None

    test_details = {'start_time': otime.utcTimeNow(),
                    'probe_asn': client_geodata['asn'],
                    'probe_cc': client_geodata['countrycode'],
                    'probe_ip': client_geodata['ip'],
                    'test_name': options['name'],
                    'test_version': options['version'],
                    'software_name': 'ooniprobe',
                    'software_version': software_version
    }
    return test_details

class OReporter(object):
    created = defer.Deferred()

    def __init__(self, cmd_line_options):
        self.cmd_line_options = dict(cmd_line_options)

    def createReport(self, options):
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
        # XXX 
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

class YAMLReporter(OReporter):
    """
    These are useful functions for reporting to YAML format.
    """
    def __init__(self, cmd_line_options):
        if cmd_line_options['reportfile'] is None:
            try:
                test_filename = os.path.basename(cmd_line_options['test'])
            except IndexError:
                raise TestFilenameNotSet

            test_name = '.'.join(test_filename.split(".")[:-1])
            frm_str = "report_%s_"+otime.timestamp()+".%s"
            reportfile = frm_str % (test_name, "yamloo")
        else:
            reportfile = cmd_line_options['reportfile']

        if os.path.exists(reportfile):
            log.msg("Report already exists with filename %s" % reportfile)
            pushFilenameStack(reportfile)

        log.debug("Creating %s" % reportfile)
        self._stream = open(reportfile, 'w+')
        OReporter.__init__(self, cmd_line_options)

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
        log.debug("Writing report with YAML reporter")
        self._write('---\n')
        self._write(safe_dump(entry))
        self._write('...\n')

    def createReport(self, options):
        self._writeln("###########################################")
        self._writeln("# OONI Probe Report for %s test" % options['name'])
        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

        test_details = getTestDetails(options)
        test_details['options'] = self.cmd_line_options

        self.writeReportEntry(test_details)

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
    def __init__(self, cmd_line_options):
        self.backend_url = cmd_line_options['collector']
        self.report_id = None

        from ooni.utils.txagentwithsocks import Agent
        from twisted.internet import reactor
        try:
            self.agent = Agent(reactor, sockshost="127.0.0.1",
                socksport=int(config.tor.socks_port))
        except Exception, e:
            log.exception(e)

        OReporter.__init__(self, cmd_line_options)

    @defer.inlineCallbacks
    def writeReportEntry(self, entry):
        log.debug("Writing report with OONIB reporter")
        content = '---\n'
        content += safe_dump(entry)
        content += '...\n'

        url = self.backend_url + '/report'

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
        url = self.backend_url + '/report'

        try:
            test_details = getTestDetails(options)
        except Exception, e:
            log.exception(e)

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
            'test_name': test_name,
            'test_version': test_version,
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
                a list of :class:ooni.reporter.OReporter

            reportEntryManager:
                an instance of :class:ooni.tasks.ReportEntryManager
        """
        self.reporters = []
        for r in reporters:
            reporter = r()
            self.reporters.append(reporter)

        self.createReports()

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
        dl = []
        for reporter in self.reporters:
            def writeReportEntry(result):
                report_write_task = ReportEntry(reporter, measurement)
                self.reportEntryManager.schedule(report_write_task)
                return report_write_task.done

            d = reporter.created.addBoth(writeReportEntry)
            dl.append(d)

        return defer.DeferredList(dl)

    def close(self, _):
        """
        Close the report by calling it's finish method.

        Returns:
            a :class:twisted.internet.defer.DeferredList that will fire when
            all the reports have been closed.

        """
        dl = []
        for reporter in self.reporters:
            d = defer.maybeDeferred(reporter.finish)
            dl.append(d)
        return defer.DeferredList(dl)


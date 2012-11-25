#-*- coding: utf-8 -*-
#
# reporter.py 
# -----------
# In here goes the logic for the creation of ooniprobe reports.
#
# :authors: Arturo Filastò, Isis Lovecruft
# :license: see included LICENSE file

import itertools
import logging
import sys
import os
import time
import yaml
import json
import traceback

from yaml.representer import *
from yaml.emitter import *
from yaml.serializer import *
from yaml.resolver import *

from scapy.packet import Packet

from twisted.python.util import untilConcludes
from twisted.trial import reporter
from twisted.internet import defer, reactor
from twisted.internet.error import ConnectionRefusedError

from ooni.utils.net import BodyReceiver, StringProducer, userAgents
from ooni.utils import otime, log, geodata

from ooni import config

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

@defer.inlineCallbacks
def getTestDetails(options):
    from ooni import __version__ as software_version

    client_geodata = {}

    if config.privacy.includeip or \
            config.privacy.includeasn or \
            config.privacy.includecountry or \
            config.privacy.includecity:
        log.msg("Running geo IP lookup via check.torproject.org")
        client_ip = yield geodata.myIP()
        client_location = geodata.IPToLocation(client_ip)
    else:
        client_ip = "127.0.0.1"

    if config.privacy.includeip:
        client_geodata['ip'] = client_ip
    else:
        client_geodata['ip'] = "127.0.0.1"

    client_geodata['asn'] = None
    client_geodata['city'] = None
    client_geodata['countrycode'] = None

    if config.privacy.includeasn:
        client_geodata['asn'] = client_location['asn']

    if config.privacy.includecity:
        client_geodata['city'] = client_location['city']

    if config.privacy.includecountry:
        client_geodata['countrycode'] = client_location['countrycode']

    test_details = {'start_time': otime.utcTimeNow(),
                    'probe_asn': client_geodata['asn'],
                    'probe_cc': client_geodata['countrycode'],
                    'probe_ip': client_geodata['ip'],
                    'test_name': options['name'],
                    'test_version': options['version'],
                    'software_name': 'ooniprobe',
                    'software_version': software_version
    }
    defer.returnValue(test_details)

class OReporter(object):
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

    def finish():
        pass

    def testDone(self, test, test_name):
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
        if os.path.exists(config.reports.yamloo):
            log.msg("Report already exists with filename %s" % config.reports.yamloo)
            log.msg("Renaming it to %s" % config.reports.yamloo+'.old')
            os.rename(config.reports.yamloo, config.reports.yamloo+'.old')

        log.debug("Creating %s" % config.reports.yamloo)
        self._stream = open(config.reports.yamloo, 'w+')
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
        return

    @defer.inlineCallbacks
    def createReport(self, options):
        self._writeln("###########################################")
        self._writeln("# OONI Probe Report for %s test" % options['name'])
        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

        test_details = yield getTestDetails(options)
        test_details['options'] = self.cmd_line_options

        self.writeReportEntry(test_details)

    def finish(self):
        self._stream.close()


class OONIBReportUpdateFailed(Exception):
    pass

class OONIBReportCreationFailed(Exception):
    pass

class OONIBTestDetailsLookupFailed(Exception):
    pass

class OONIBReporter(OReporter):
    def __init__(self, cmd_line_options):
        self.backend_url = cmd_line_options['collector']

        from ooni.utils.txagentwithsocks import Agent
        from twisted.internet import reactor
        try:
            self.agent = Agent(reactor, sockshost="127.0.0.1",
                socksport=int(config.advanced.tor_socksport))
        except Exception, e:
            log.exception(e)

        OReporter.__init__(self, cmd_line_options)

    @defer.inlineCallbacks
    def writeReportEntry(self, entry):
        log.debug("Writing report with OONIB reporter")
        content = '---\n'
        content += safe_dump(entry)
        content += '...\n'

        url = self.backend_url + '/report/new'

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
            # XXX we must trap this in the runner and make sure to report the data later.
            log.err("Error in writing report entry")
            raise OONIBReportUpdateFailed

        #parsed_response = json.loads(backend_response)
        #self.report_id = parsed_response['report_id']
        #self.backend_version = parsed_response['backend_version']
        #log.debug("Created report with id %s" % parsed_response['report_id'])


    @defer.inlineCallbacks
    def createReport(self, options):
        """
        Creates a report on the oonib collector.
        """
        test_name = options['name']
        test_version = options['version']

        log.debug("Creating report with OONIB Reporter")
        url = self.backend_url + '/report/new'
        software_version = '0.0.1'

        test_details = yield getTestDetails(options)
        test_details['options'] = self.cmd_line_options

        content = '---\n'
        content += safe_dump(test_details)
        content += '...\n'

        request = {'software_name': 'ooniprobe',
            'software_version': software_version,
            'test_name': test_name,
            'test_version': test_version,
            'progress': 0,
            'content': content
        }
        log.debug("Creating report via url %s" % url)
        request_json = json.dumps(request)
        log.debug("Sending %s" % request_json)

        bodyProducer = StringProducer(json.dumps(request))

        try:
            response = yield self.agent.request("POST", url,
                                bodyProducer=bodyProducer)
        except ConnectionRefusedError:
            log.err("Connection to reporting backend failed (ConnectionRefusedError)")
            raise OONIBReportCreationFailed
        except Exception, e:
            log.exception(e)
            raise OONIBReportCreationFailed

        # This is a little trix to allow us to unspool the response. We create
        # a deferred and call yield on it.
        response_body = defer.Deferred()
        response.deliverBody(BodyReceiver(response_body))

        backend_response = yield response_body

        try:
            parsed_response = json.loads(backend_response)
        except Exception, e:
            log.exception(e)
            raise OONIBReportCreationFailed

        self.report_id = parsed_response['report_id']
        self.backend_version = parsed_response['backend_version']
        log.debug("Created report with id %s" % parsed_response['report_id'])


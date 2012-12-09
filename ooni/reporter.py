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
import time
import yaml
import json
import traceback

from twisted.python.util import untilConcludes
from twisted.trial import reporter
from twisted.internet import defer, reactor

from ooni import config
from ooni.templates.httpt import BodyReceiver, StringProducer
from ooni.utils import otime, log, geodata
from ooni.utils.hacks import OSafeRepresenter, OSafeDumper

try:
    from scapy.all import packet
except:
    class FooClass:
        Packet = object
    packet = FooClass

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
        log.msg("Running geoIP lookup via check.torproject.org")
        if config.privacy.checktimeout is not None and \
                isinstance(config.privacy.checktimeout, int):
            my_ip_timeout = config.privacy.checktimeout
        else:
            log.debug(
                "reporter.getTestDetails(): bad config.privacy.checktimeout %s"
                % str(config.privacy.checktimeout)
                )
            my_ip_timeout = 15
        client_ip = yield geodata.myIP(connectTimeout=my_ip_timeout)
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
    def createReport(options):
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
        log.debug("Calling reporter to record results")
        test_report = dict(test.report)

        if isinstance(test.input, packet.Packet):
            test_input = createPacketReport(test.input)
        else:
            test_input = test.input

        test_started = test._start_time
        test_runtime = test_started - time.time()

        report = {'input': test_input,
                'test_name': test_name,
                'test_started': test_started,
                'report': test_report}
        return self.writeReportEntry(report)

    def allDone(self):
        log.debug("Running pending timed reactor calls")
        reactor.runUntilCurrent()
        if reactor.running:
            log.debug("Reactor running. Stopping the reactor...")
            try:
                reactor.stop()
            except:
                log.debug("Unable to stop the reactor")
        return None

class YAMLReporter(OReporter):
    """
    These are useful functions for reporting to YAML format.
    """
    def __init__(self, stream):
        self._stream = stream

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

    @defer.inlineCallbacks
    def createReport(self, options):
        self._writeln("###########################################")
        self._writeln("# OONI Probe Report for %s test" % options['name'])
        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

        test_details = yield getTestDetails(options)

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
    def __init__(self, backend_url):
        from twisted.web.client import Agent
        from twisted.internet import reactor
        self.agent = Agent(reactor)
        self.backend_url = backend_url

    @defer.inlineCallbacks
    def writeReportEntry(self, entry):
        log.debug("Writing report with OONIB reporter")
        content = '---\n'
        content += safe_dump(entry)
        content += '...\n'

        url = self.backend_url + '/report/new'

        request = {'report_id': self.report_id,
                'content': content}

        log.debug("Updating report with id %s" % self.report_id)
        request_json = json.dumps(request)
        log.debug("Sending %s" % request_json)

        bodyProducer = StringProducer(json.dumps(request))
        log.debug("Creating report via url %s" % url)

        try:
            response = yield self.agent.request("PUT", url, 
                                bodyProducer=bodyProducer)
        except:
            # XXX we must trap this in the runner and make sure to report the
            # data later.
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
        log.debug("Creating report via url %s" % url)

        try:
            response = yield self.agent.request("POST", url, 
                                bodyProducer=bodyProducer)
        except:
            raise OONIBReportCreationFailed

        # This is a little trix to allow us to unspool the response. We create
        # a deferred and call yield on it.
        response_body = defer.Deferred()
        response.deliverBody(BodyReceiver(response_body))

        backend_response = yield response_body

        parsed_response = json.loads(backend_response)
        self.report_id = parsed_response['report_id']
        self.backend_version = parsed_response['backend_version']
        log.debug("Created report with id %s" % parsed_response['report_id'])


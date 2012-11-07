import itertools
import logging
import sys
import time
import yaml
import json
import traceback

from yaml.representer import *
from yaml.emitter import *
from yaml.serializer import *
from yaml.resolver import *

from datetime import datetime
from twisted.python.util import untilConcludes
from twisted.trial import reporter
from twisted.internet import defer

from ooni.templates.httpt import BodyReceiver, StringProducer
from ooni.utils import date, log, geodata

try:
    ## Get rid of the annoying "No route found for
    ## IPv6 destination warnings":
    logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
    from scapy.all import packet
except:
    class FooClass:
        Packet = object
    packet = FooClass

pyunit =  __import__('unittest')

class OSafeRepresenter(SafeRepresenter):
    """
    This is a custom YAML representer that allows us to represent reports
    safely.
    It extends the SafeRepresenter to be able to also represent complex numbers
    """
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


def safe_dump(data, stream=None, **kw):
    """
    Safely dump to a yaml file the specified data.
    """
    return yaml.dump_all([data], stream, Dumper=OSafeDumper, **kw)

class OONIBReporter(object):
    def __init__(self, backend_url):
        from twisted.web.client import Agent
        from twisted.internet import reactor

        self.agent = Agent(reactor)
        self.backend_url = backend_url

    def _newReportCreated(self, data):
        #log.debug("Got this as result: %s" % data)
        print "Got this as result: %s" % data

        return data

    def _processResponseBody(self, response, body_cb):
        #log.debug("Got response %s" % response)
        print "Got response %s" % response

        done = defer.Deferred()
        response.deliverBody(BodyReceiver(done))
        done.addCallback(body_cb)
        return done

    def newReport(self, test_name, test_version):
        url = self.backend_url + '/new'
        print "Creating report via url %s" % url

        software_version = '0.0.1'

        request = {'software_name': 'ooni-probe',
                'software_version': software_version,
                'test_name': test_name, 'test_version': test_version,
                'progress': 0}

        #log.debug("Creating report via url %s" % url)
        bodyProducer = StringProducer(json.dumps(request))
        d = self.agent.request("POST", url, bodyProducer=bodyProducer)
        d.addCallback(self._processResponseBody, self._newReportCreated)
        return d


class OReporter(pyunit.TestResult):
    """
    This is an extension of the unittest TestResult. It adds support for
    reporting to yaml format.
    """
    reporterFactory = None

    def __init__(self, stream=sys.stdout, tbformat='default', realtime=False,
                 publisher=None, testSuite=None):
        super(OReporter, self).__init__()
        self.report = {'tests': []}
        self._stream = reporter.SafeStream(stream)
        self.tbformat = tbformat
        self.realtime = realtime
        self._startTime = None
        self._warningCache = set()

        self._publisher = publisher

    def _getTime(self):
        return time.time()

    def _write(self, format_string, *args):
        s = str(format_string)
        assert isinstance(s, type(''))
        if args:
            self._stream.write(s % args)
        else:
            self._stream.write(s)
        untilConcludes(self._stream.flush)

    def _writeln(self, format_string, *args):
        self._write(format_string, *args)
        self._write('\n')

    def writeYamlLine(self, line):
        to_write = safe_dump([line])
        self._write(to_write)


class ReporterFactory(OReporter):
    """
    This is a reporter factory. It emits new instances of Reports. It is also
    responsible for writing the OONI Report headers.
    """
    firstrun = True

    def __init__(self, stream=sys.stdout, tbformat='default', realtime=False,
                 publisher=None, testSuite=None):
        super(ReporterFactory, self).__init__(stream=stream,
                tbformat=tbformat, realtime=realtime, publisher=publisher)

        self._testSuite = testSuite
        self._reporters = []

    @defer.inlineCallbacks
    def writeHeader(self):
        self.firstrun = False
        options = self.options
        self._writeln("###########################################")
        self._writeln("# OONI Probe Report for %s test" % options['name'])
        self._writeln("# %s" % date.pretty_date())
        self._writeln("###########################################")

        client_geodata = {}
        log.msg("Running geo IP lookup via check.torproject.org")

        client_geodata['ip'] = yield geodata.myIP()
        client_geodata['asn'] = 'unknown'
        client_geodata['city'] = 'unknown'
        client_geodata['countrycode'] = 'unknown'

        try:
            import txtorcon
            client_location = txtorcon.util.NetLocation(client_geodata['ip'])
            client_geodata['asn'] = client_location.asn
            client_geodata['city'] = client_location.city
            client_geodata['countrycode'] = client_location.countrycode
        except ImportError:
            log.err("txtorcon is not installed. Geolocation lookup is not"\
                    "supported")

        test_details = {'start_time': repr(date.now()),
                        'probe_asn': client_geodata['asn'],
                        'probe_cc': client_geodata['countrycode'],
                        'probe_ip': client_geodata['ip'],
                        'test_name': options['name'],
                        'test_version': options['version'],
                        }

        self.writeYamlLine(test_details)
        self._writeln('')

    def create(self):
        r = OONIReporter(self._stream, self.tbformat, self.realtime,
                         self._publisher)
        self._reporters.append(OONIReporter)
        return r


class OONIReporter(OReporter):
    """
    This is a special reporter that has knowledge about the fact that there can
    exist more test runs of the same kind per run.
    These multiple test runs are kept track of through idx.

    An instance of such reporter should be created per InputUnit. Every input
    unit will invoke size_of_input_unit * test_cases times startTest().
    """
    def __init__(self, stream=sys.stdout, tbformat='default', realtime=False,
                 publisher=None):
        super(OONIReporter, self).__init__(stream=stream,
                    tbformat=tbformat, realtime=realtime, publisher=publisher)

        self._tests = {}

    def getTestIndex(self, test):
        try:
            idx = test._idx
        except:
            idx = 0
        return idx


    def startTest(self, test):
        super(OONIReporter, self).startTest(test)

        idx = self.getTestIndex(test)
        if not self._startTime:
            self._startTime = self._getTime()

        log.debug("Starting test %s" % idx)
        test.report = {}

        self._tests[idx] = {}
        self._tests[idx]['test_started'] = self._getTime()

        if isinstance(test.input, packet.Packet):
            test_input = repr(test.input)
        else:
            test_input = test.input

        self._tests[idx]['input'] = test_input
        self._tests[idx]['name'] = test.name
        log.debug("Now starting %s" % self._tests[idx])


    def stopTest(self, test):
        log.debug("Stopping test")
        super(OONIReporter, self).stopTest(test)

        idx = self.getTestIndex(test)

        self._tests[idx]['last_time'] = self._getTime() - \
                                        self._tests[idx]['test_started']

        # XXX I put a dict() here so that the object is re-instantiated and I
        #     actually end up with the report I want. This could either be a
        #     python bug or a yaml bug.
        report = dict(test.report)
        log.debug("Set the report to be a dict")

        log.debug("Adding to report %s" % report)
        self._tests[idx]['report'] = report


    def done(self):
        """
        Summarize the result of the test run.

        The summary includes a report of all of the errors, todos, skips and
        so forth that occurred during the run. It also includes the number of
        tests that were run and how long it took to run them (not including
        load time).

        Expects that L{_printErrors}, L{_writeln}, L{_write}, L{_printSummary}
        and L{_separator} are all implemented.
        """
        log.debug("Test run concluded")
        if self._startTime is not None:
            self.report['start_time'] = self._startTime
            self.report['run_time'] = time.time() - self._startTime
            self.report['tests_run'] = self.testsRun
        self.report['tests'] = self._tests
        self.writeReport()

    def writeReport(self):
        self.writeYamlLine(self.report)

    def addSuccess(self, test):
        OReporter.addSuccess(self, test)
        #self.report['result'] = {'value': 'success'}

    def addError(self, test, exception):
        OReporter.addError(self, test, exception)
        exc_type, exc_value, exc_traceback = exception
        log.err(exc_type)
        log.err(str(exc_value))
        # XXX properly print out the traceback
        for line in '\n'.join(traceback.format_tb(exc_traceback)).split("\n"):
            log.err(line)

    def addFailure(self, *args):
        OReporter.addFailure(self, *args)
        log.warn(args)

    def addSkip(self, *args):
        OReporter.addSkip(self, *args)
        #self.report['result'] = {'value': 'skip', 'args': args}

    def addExpectedFailure(self, *args):
        OReporter.addExpectedFailure(self, *args)
        #self.report['result'] = {'value': 'expectedFailure', 'args': args}

    def addUnexpectedSuccess(self, *args):
        OReporter.addUnexpectedSuccess(self, *args)
        #self.report['result'] = {'args': args, 'value': 'unexpectedSuccess'}



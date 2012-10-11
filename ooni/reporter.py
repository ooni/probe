import copy_reg
import itertools
import logging
import sys
import time
import yaml

from yaml.representer import *
from yaml.emitter import *
from yaml.serializer import *
from yaml.resolver import *

from datetime import datetime
from twisted.python.util import OrderedDict, untilConcludes
from twisted.trial import unittest, reporter, runner
from twisted.internet import defer
from ooni.utils import date, log, geodata

try:
    ## Get rid of the annoying "No route found for 
    ## IPv6 destination warnings":
    logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
    from scapy.all import packet
except:
    class FooClass:
        pass
    packet = object
    packet.Packet = FooClass


pyunit =  __import__('unittest')

class OSafeRepresenter(SafeRepresenter):
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
    return yaml.dump_all([data], stream, Dumper=OSafeDumper, **kw)

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

    def _write(self, format, *args):
        s = str(format)
        assert isinstance(s, type(''))
        if args:
            self._stream.write(s % args)
        else:
            self._stream.write(s)
        untilConcludes(self._stream.flush)

    def _writeln(self, format, *args):
        self._write(format, *args)
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

        client_ip = yield geodata.myIP()
        try:
            import txtorcon
            client_location = txtorcon.util.NetLocation(client_ip)
        except:
            log.err("txtorcon is not installed. Geolocation lookup is not"\
                    "supported")

        client_geodata['ip'] = client_ip
        client_geodata['asn'] = client_location.asn
        client_geodata['city'] = client_location.city
        client_geodata['countrycode'] = client_location.countrycode

        test_details = {'startTime': repr(date.now()),
                        'probeASN': client_geodata['asn'],
                        'probeCC': client_geodata['countrycode'],
                        'probeIP': client_geodata['ip'],
                        'probeLocation': {'city': client_geodata['city'],
                                          'countrycode':
                                          client_geodata['countrycode']},
                        'testName': options['name'],
                        'testVersion': options['version'],
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
        self._publisher = publisher
        if publisher is not None:
            publisher.addObserver(self._observeWarnings)

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

        test.report = {}

        self._tests[idx] = {}
        self._tests[idx]['testStarted'] = self._getTime()
        if isinstance(test.input, packet.Packet):
            test_input = repr(test.input)
        else:
            test_input = test.input

        self._tests[idx]['input'] = test_input
        #self._tests[idx]['idx'] = idx
        self._tests[idx]['name'] = test.name
        #self._tests[idx]['test'] = test
        print "Now starting %s" % self._tests[idx]


    def stopTest(self, test):
        super(OONIReporter, self).stopTest(test)

        idx = self.getTestIndex(test)

        self._tests[idx]['lastTime'] = self._getTime() - self._tests[idx]['testStarted']
        # This is here for allowing reporting of legacy tests.
        # XXX In the future this should be removed.
        try:
            report = list(test.legacy_report)
        except:
            # XXX I put a dict() here so that the object is re-instantiated and I
            #     actually end up with the report I want. This could either be a
            #     python bug or a yaml bug.
            report = dict(test.report)

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
        if self._publisher is not None:
            self._publisher.removeObserver(self._observeWarnings)
        if self._startTime is not None:
            self.report['startTime'] = self._startTime
            self.report['runTime'] = time.time() - self._startTime
            self.report['testsRun'] = self.testsRun
        self.report['tests'] = self._tests
        self.writeReport()

    def writeReport(self):
        self.writeYamlLine(self.report)

    def addSuccess(self, test):
        super(OONIReporter, self).addSuccess(test)
        #self.report['result'] = {'value': 'success'}

    def addError(self, *args):
        super(OONIReporter, self).addError(*args)
        #self.report['result'] = {'value': 'error', 'args': args}

    def addFailure(self, *args):
        super(OONIReporter, self).addFailure(*args)
        #self.report['result'] = {'value': 'failure', 'args': args}

    def addSkip(self, *args):
        super(OONIReporter, self).addSkip(*args)
        #self.report['result'] = {'value': 'skip', 'args': args}

    def addExpectedFailure(self, *args):
        super(OONIReporter, self).addExpectedFailure(*args)
        #self.report['result'] = {'value': 'expectedFailure', 'args': args}

    def addUnexpectedSuccess(self, *args):
        super(OONIReporter, self).addUnexpectedSuccess(*args)
        #self.report['result'] = {'args': args, 'value': 'unexpectedSuccess'}



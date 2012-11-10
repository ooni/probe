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

from yaml.representer import *
from yaml.emitter import *
from yaml.serializer import *
from yaml.resolver import *

from twisted.python.util import untilConcludes
from twisted.trial import reporter
from twisted.internet import defer, reactor

from ooni.templates.httpt import BodyReceiver, StringProducer
from ooni.utils import otime, log, geodata
from ooni import config

try:
    ## Get rid of the annoying "No route found for
    ## IPv6 destination warnings":
    logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
    from scapy.all import packet
except:
    class FooClass:
        Packet = object
    packet = FooClass

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


class YamlReporter(object):
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
        self._write('---\n')
        self._write(safe_dump(entry))
        self._write('...\n')

    def finish(self):
        self._stream.close()

class OReporter(YamlReporter):
    """
    This is a reporter factory. It emits new instances of Reports. It is also
    responsible for writing the OONI Report headers.
    """
    def writeTestsReport(self, tests):
        for test in tests.values():
            self.writeReportEntry(test)

    @defer.inlineCallbacks
    def writeReportHeader(self, options):
        self.firstrun = False
        self._writeln("###########################################")
        self._writeln("# OONI Probe Report for %s test" % options['name'])
        self._writeln("# %s" % otime.prettyDateNow())
        self._writeln("###########################################")

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
                        }
        self.writeReportEntry(test_details)

    def testDone(self, test):
        test_report = dict(test.report)

        # XXX the scapy test has an example of how 
        # to do this properly.
        if isinstance(test.input, packet.Packet):
            test_input = repr(test.input)
        else:
            test_input = test.input

        test_started = test._start_time
        test_runtime = test_started - time.time()

        report = {'input': test_input,
                'test_started': test_started,
                'report': test_report}
        self.writeReportEntry(report)

    def allDone(self):
        log.debug("allDone: Finished running all tests")
        self.finish()
        try:
            reactor.stop()
        except:
            pass
        return None


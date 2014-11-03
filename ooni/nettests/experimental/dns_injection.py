# -*- encoding: utf-8 -*-
from twisted.python import usage
from twisted.internet import defer

from ooni.templates import dnst
from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [
            ['resolver', 'r', '8.8.8.1', 'an invalid DNS resolver'],
            ['timeout', 't', 3, 'timeout after which we should consider the query failed']
    ]

class DNSInjectionTest(dnst.DNSTest):
    """
    This test detects DNS spoofed DNS responses by performing UDP based DNS
    queries towards an invalid DNS resolver.

    For it to work we must be traversing the network segment of a machine that
    is actively injecting DNS query answers.
    """
    name = "DNS Injection"
    description = "Checks for injection of spoofed DNS answers"
    version = "0.1"
    authors = "Arturo Filastò"

    inputFile = ['file', 'f', None,
                 'Input file of list of hostnames to attempt to resolve']

    usageOptions = UsageOptions
    requiredOptions = ['resolver', 'file']
    requiresRoot = False
    requiresTor = False

    def setUp(self):
        self.resolver = (self.localOptions['resolver'], 53)
        self.queryTimeout = [self.localOptions['timeout']]

    def inputProcessor(self, filename):
        fp = open(filename)
        for line in fp:
            if line.startswith('http://'):
                yield line.replace('http://', '').replace('/', '').strip()
            else:
                yield line.strip()
        fp.close()

    def test_injection(self):
        self.report['injected'] = None

        d = self.performALookup(self.input, self.resolver)
        @d.addCallback
        def cb(res):
            log.msg("The DNS query for %s is injected" % self.input)
            self.report['injected'] = True

        @d.addErrback
        def err(err):
            err.trap(defer.TimeoutError)
            log.msg("The DNS query for %s is not injected" % self.input)
            self.report['injected'] = False

        return d


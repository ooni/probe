# -*- encoding: utf-8 -*-
#
#
#  dnstamper
#  *********
#
#  The test reports censorship if the cardinality of the intersection of
#  the query result set from the control server and the query result set
#  from the experimental server is zero, which is to say, if the two sets
#  have no matching results whatsoever.
#
#  NOTE: This test frequently results in false positives due to GeoIP-based
#  load balancing on major global sites such as google, facebook, and
#  youtube, etc.
#
# :authors: Arturo Filastò, Isis Lovecruft
# :licence: see LICENSE

from ooni import nettest
from ooni.utils import log
from twisted.internet import defer
from twisted.names import client
from twisted.names.error import DNSQueryRefusedError

class DNSTamperTest(nettest.TestCase):

    name = "DNS tamper"

    description = "DNS censorship detection test"
    version = '0.2'

    lookupTimeout = [1]

    requirements = None
    inputFile = ['file', 'f', None,
                 'Input file of list of hostnames to attempt to resolve']

    optParameters = [['controlresolver', 'c', '8.8.8.8',
                      'Known good DNS server'],
                     ['testresolvers', 't', None,
                      'file containing list of DNS resolvers to test against']
                     ]

    def setUp(self):
        self.report['test_lookups'] = {}
        self.report['test_reverse'] = {}

        self.report['control_lookup'] = []

        self.report['a_lookups'] = {}

        self.report['tampering'] = {}

        self.test_a_lookups = {}
        self.control_a_lookups = []

        self.control_reverse = None
        self.test_reverse = {}

        if not self.localOptions['testresolvers']:
            self.test_resolvers = ['8.8.8.8']
            return

        try:
            fp = open(self.localOptions['testresolvers'])
        except:
            raise usage.UsageError("Invalid test resolvers file")

        self.test_resolvers = [x.strip() for x in fp.readlines()]
        fp.close()

    def process_a_answers(self, answers, resolver):
        print "Processing A answers for %s" % resolver
        all_a = []
        a_a = []
        for answer in answers[0]:
            if answer.type is 1:
                # A type query
                r = answer.payload.dottedQuad()
                self.report['a_lookups'][resolver] = r
                a_a.append(r)
            lookup = str(answer.payload)
            all_a.append(lookup)

        if resolver == 'control':
            self.report['control_server'] = self.localOptions['controlresolver']
            self.report['control_lookup'] = all_a
            self.control_a_lookups = a_a
        else:
            self.test_a_lookups[resolver] = a_a
            self.report['test_lookups'][resolver] = all_a
        print "Done"

    def process_ptr_answers(self, answers, resolver):
        print "Processing PTR answers for %s" % resolver
        name = None
        for answer in answers[0]:
            if answer.type is 12:
                # PTR type
                name = str(answer.payload.name)

        if resolver == 'control':
            self.control_reverse = name
            self.report['control_reverse'] = name
        else:
            self.test_reverse[resolver] = name
            self.report['test_reverse'][resolver] = name

    def ptr_lookup_error(self, failure, resolver):
    #def ptr_lookup_error(self, *arg, **kw):
        print "There was an error in PTR lookup %s" % resolver
        print failure
        if resolver == 'control':
            self.report['control_reverse'] = None
        else:
            self.report['test_reverse'][resolver] = None

    def a_lookup_error(self, failure, resolver):
        print "There was an error in A lookup %s" % resolver

        if failure.type is DNSQueryRefusedError:
            self.report['tampering'][resolver] = 'connection-refused'
        elif failure.type is defer.TimeoutError:
            self.report['tampering'][resolver] = 'timeout'

        if resolver == 'control':
            self.report['control_lookup'] = None
        else:
            self.report['test_lookups'][resolver] = None
            self.test_a_lookups[resolver] = None

    def test_lookup(self):
        print "Doing the test lookups on %s" % self.input
        list_of_ds = []
        hostname = self.input

        resolver = [(self.localOptions['controlresolver'], 53)]
        res = client.createResolver(servers=resolver, resolvconf='')

        control_r = res.lookupAddress(hostname, timeout=self.lookupTimeout)
        control_r.addCallback(self.process_a_answers, 'control')
        control_r.addErrback(self.a_lookup_error, 'control')

        for test_resolver in self.test_resolvers:
            print "Going for %s" % test_resolver
            resolver = [(test_resolver, 53)]
            res = client.createResolver(servers=resolver, resolvconf='')
            #res = self.createResolver(servers=resolver)

            d = res.lookupAddress(hostname, timeout=self.lookupTimeout)
            d.addCallback(self.process_a_answers, test_resolver)
            d.addErrback(self.a_lookup_error, test_resolver)
            list_of_ds.append(d)

        list_of_ds.append(control_r)
        dl = defer.DeferredList(list_of_ds)
        dl.addCallback(self.do_reverse_lookups)
        dl.addBoth(self.compare_results)
        return dl

    def reverse_lookup(self, address, resolver):
        ptr = '.'.join(address.split('.')[::-1]) + '.in-addr.arpa'
        r = resolver.lookupPointer(ptr, self.lookupTimeout)
        return r

    def do_reverse_lookups(self, result):
        print "Doing the reverse lookups %s" % self.input
        list_of_ds = []

        resolver = [(self.localOptions['controlresolver'], 53)]
        res = self.createResolver(servers=resolver)

        test_reverse = self.reverse_lookup(self.control_a_lookups[0], res,
                timeout=self.lookupTimeout)
        test_reverse.addCallback(self.process_ptr_answers, 'control')
        test_reverse.addErrback(self.ptr_lookup_error, 'control')

        list_of_ds.append(test_reverse)

        for test_resolver in self.test_resolvers:
            try:
                ip = self.test_a_lookups[test_resolver][0]
            except:
                break

            d = self.reverse_lookup(ip, res)
            d.addCallback(self.process_ptr_answers, test_resolver)
            d.addErrback(self.ptr_lookup_error, test_resolver)
            list_of_ds.append(d)

        dl = defer.DeferredList(list_of_ds)
        return dl

    def compare_results(self, *arg, **kw):
        print "Comparing results for %s" % self.input
        print self.test_a_lookups

        for test, test_a_lookups in self.test_a_lookups.items():
            print "Now doing %s | %s" % (test, test_a_lookups)
            if not test_a_lookups:
                self.report['tampering'][test] = 'unknown'
                continue

            if set(test_a_lookups) & set(self.control_a_lookups):
                # Address has not tampered with on DNS server
                self.report['tampering'][test] = False

            elif self.control_reverse and set([self.control_reverse]) & set([self.report['test_reverse'][test]]):
                # Further testing has eliminated false positives
                self.report['tampering'][test] = 'reverse-match'

            else:
                # Reverse DNS on the results returned by returned
                # which does not match the expected domainname
                self.report['tampering'][test] = True

        if len(self.test_a_lookups) == len(self.test_resolvers):
            self.end()
        else:
            print "Still missing %s - %s" % (len(self.test_a_lookups),
                    len(self.test_resolvers))


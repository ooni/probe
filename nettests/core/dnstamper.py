# -*- encoding: utf-8 -*-
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

import pdb

from twisted.python import usage
from twisted.internet import defer

from ooni.templates import dnst

from ooni import nettest
from ooni.utils import log

class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', '8.8.8.8:53',
                        'The OONI backend that runs the DNS resolver'],
                     ['testresolvers', 'T', None,
                        'File containing list of DNS resolvers to test against'],
                     ['testresolver', 't', None,
                         'Specify a single test resolver to use for testing']
                    ]

class DNSTamperTest(dnst.DNSTest):

    name = "DNS tamper"
    description = "DNS censorship detection test"
    version = "0.3"
    authors = "Arturo Filastò, Isis Lovecruft"
    requirements = None

    inputFile = ['file', 'f', None,
                 'Input file of list of hostnames to attempt to resolve']

    usageOptions = UsageOptions
    requiredOptions = ['backend', 'file']

    def setUp(self):
        if not self.localOptions['testresolvers']:
            raise usage.UsageError("You did not specify a file of DNS servers to test!"
                                   "See the '--testresolvers' option.")

        try:
            fp = open(self.localOptions['testresolvers'])
        except:
            raise usage.UsageError("Invalid test resolvers file")

        self.test_resolvers = [x.strip() for x in fp.readlines()]
        fp.close()

        dns_ip, dns_port = self.localOptions['backend'].split(':')
        self.control_dns_server = (dns_ip, int(dns_port))

        self.report['test_resolvers'] = self.test_resolvers
        self.report['control_resolver'] = self.control_dns_server

    @defer.inlineCallbacks
    def test_a_lookup(self):
        """
        We perform an A lookup on the DNS test servers for the domains to be
        tested and an A lookup on the known good DNS server.

        We then compare the results from test_resolvers and that from
        control_resolver and see if the match up.
        If they match up then no censorship is happening (tampering: false).

        If they do not we do a reverse lookup (PTR) on the test_resolvers and
        the control resolver for every IP address we got back and check to see
        if anyone of them matches the control ones.

        If they do then we take not of the fact that censorship is probably not
        happening (tampering: reverse-match).

        If they do not match then censorship is probably going on (tampering:
        true).
        """
        log.msg("Doing the test lookups on %s" % self.input)
        list_of_ds = []
        hostname = self.input

        self.report['tampering'] = {}

        control_answers = yield self.performALookup(hostname, self.control_dns_server)

        for test_resolver in self.test_resolvers:
            log.msg("Going for %s" % test_resolver)
            test_dns_server = (test_resolver, 53)

            experiment_answers = yield self.performALookup(hostname, test_dns_server)
            log.debug("Got these answers %s" % experiment_answers)

            if not experiment_answers:
                log.err("Got no response, perhaps the DNS resolver is down?")
                self.report['tampering'][test_resolver] = 'no_answer'
                continue

            log.debug("Comparing %s with %s" % (experiment_answers, control_answers))
            if set(experiment_answers) & set(control_answers):
                log.msg("Address has not tampered with on DNS server")
                self.report['tampering'][test_resolver] = False
            else:
                log.msg("Trying to do reverse lookup")

                experiment_reverse = yield self.performPTRLookup(experiment_answers[0], test_dns_server)
                control_reverse = yield self.performPTRLookup(control_answers[0], self.control_dns_server)

                if experiment_reverse == control_reverse:
                    log.msg("Further testing has eliminated false positives")
                    self.report['tampering'][test_resolver] = 'reverse_match'
                else:
                    log.msg("Reverse DNS on the results returned by returned")
                    log.msg("which does not match the expected domainname")
                    self.report['tampering'][test_resolver] = True


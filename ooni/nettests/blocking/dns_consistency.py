# -*- encoding: utf-8 -*-
#
#  dnsconsistency
#  **************
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


from twisted.python import usage
from twisted.internet import defer

from ooni.templates import dnst

from ooni.utils import log


class UsageOptions(usage.Options):
    optParameters = [['backend', 'b', None,
                      'The OONI backend that runs the DNS resolver.'],
                     ['testresolvers', 'T', None,
                      'File containing list of DNS resolvers to test against.'],
                     ['testresolver', 't', None,
                         'Specify a single test resolver to use for testing.']
                     ]


class DNSConsistencyTest(dnst.DNSTest):

    name = "DNS Consistency"
    description = "Checks to see if the DNS responses from a "\
                  "set of DNS resolvers are consistent."
    version = "0.7.0"
    authors = "Arturo Filastò, Isis Lovecruft"

    inputFile = ['file', 'f', None,
                 'Input file of list of hostnames to attempt to resolve']

    requiredTestHelpers = {'backend': 'dns'}
    requiresRoot = False
    requiresTor = False

    usageOptions = UsageOptions
    requiredOptions = ['backend', 'file']

    def setUp(self):
        if (not self.localOptions['testresolvers'] and
                not self.localOptions['testresolver']):
            self.test_resolvers = []
            with open('/etc/resolv.conf') as f:
                for line in f:
                    if line.startswith('nameserver'):
                        self.test_resolvers.append(line.split(' ')[1].strip())
            self.report['test_resolvers'] = self.test_resolvers

        elif self.localOptions['testresolvers']:
            test_resolvers_file = self.localOptions['testresolvers']

        elif self.localOptions['testresolver']:
            self.test_resolvers = [self.localOptions['testresolver']]

        try:
            with open(test_resolvers_file) as f:
                self.test_resolvers = [
                    x.split('#')[0].strip() for x in f.readlines()]
                self.report['test_resolvers'] = self.test_resolvers
            f.close()

        except IOError as e:
            log.exception(e)
            raise usage.UsageError("Invalid test resolvers file")

        except NameError:
            log.debug("No test resolver file configured")

        dns_ip, dns_port = self.localOptions['backend'].split(':')
        self.control_dns_server = (str(dns_ip), int(dns_port))

        self.report['control_resolver'] = "%s:%d" % self.control_dns_server

    @defer.inlineCallbacks
    def test_a_lookup(self):
        """
        We perform an A lookup on the DNS test servers for the domains to be
        tested and an A lookup on the known good DNS server.

        We then compare the results from test_resolvers and that from
        control_resolver and see if they match up.
        If they match up then no censorship is happening (tampering: false).

        If they do not we do a reverse lookup (PTR) on the test_resolvers and
        the control resolver for every IP address we got back and check to see
        if anyone of them matches the control ones.

        If they do, then we take note of the fact that censorship is probably
        not happening (tampering: reverse-match).

        If they do not match then censorship is probably going on (tampering:
        true).
        """
        log.msg("Doing the test lookups on %s" % self.input)
        hostname = self.input

        self.report['successful'] = []
        self.report['failures'] = []
        self.report['inconsistent'] = []

        self.report['errors'] = {}

        try:
            control_answers = yield self.performALookup(hostname,
                                                        self.control_dns_server)

            if not control_answers:
                log.err(
                    "Got no response from control DNS server %s:%d, "
                    "perhaps the DNS resolver is down?" %
                    self.control_dns_server)
                self.report['errors'][
                    "%s:%d" %
                    self.control_dns_server] = 'no_answer'
        except:
            self.report['errors'][
                "%s:%d" %
                self.control_dns_server] = 'error'
            control_answers = None

        for test_resolver in self.test_resolvers:
            log.msg("Testing resolver: %s" % test_resolver)
            test_dns_server = (test_resolver, 53)

            try:
                experiment_answers = yield self.performALookup(hostname,
                                                               test_dns_server)
            except Exception:
                log.err("Problem performing the DNS lookup")
                self.report['errors'][test_resolver] = 'dns_lookup_error'
                self.report['failures'].append(test_resolver)
                continue

            if not experiment_answers:
                log.err("Got no response, perhaps the DNS resolver is down?")
                self.report['errors'][test_resolver] = 'no_answer'
                self.report['failures'].append(test_resolver)
                continue
            else:
                log.debug(
                    "Got the following A lookup answers %s from %s" %
                    (experiment_answers, test_resolver))

            def lookup_details():
                """
                A closure useful for printing test details.
                """
                log.msg("test resolver: %s" % test_resolver)
                log.msg("experiment answers: %s" % experiment_answers)
                log.msg("control answers: %s" % control_answers)

            log.debug(
                "Comparing %s with %s" %
                (experiment_answers, control_answers))

            if not control_answers:
                log.msg("Skipping control resolver comparison")
                self.report['errors'][test_resolver] = None

            elif set(experiment_answers) & set(control_answers):
                lookup_details()
                log.msg("tampering: false")
                self.report['errors'][test_resolver] = False
                self.report['successful'].append(test_resolver)
            else:
                log.msg("Trying to do reverse lookup")
                experiment_reverse = yield self.performPTRLookup(experiment_answers[0],
                                                                 test_dns_server)
                control_reverse = yield self.performPTRLookup(control_answers[0],
                                                              self.control_dns_server)

                if experiment_reverse == control_reverse:
                    log.msg("Further testing has eliminated false positives")
                    lookup_details()
                    log.msg("tampering: reverse_match")
                    self.report['errors'][test_resolver] = 'reverse_match'
                    self.report['successful'].append(test_resolver)
                else:
                    log.msg("Reverse lookups do not match")
                    lookup_details()
                    log.msg("tampering: true")
                    self.report['errors'][test_resolver] = True
                    self.report['inconsistent'].append(test_resolver)

    def inputProcessor(self, filename=None):
        """
        This inputProcessor extracts domain names from urls
        """
        log.debug("Running dnsconsistency default processor")
        if filename:
            fp = open(filename)
            for x in fp.readlines():
                yield x.strip().split('//')[-1].split('/')[0]
            fp.close()
        else:
            pass

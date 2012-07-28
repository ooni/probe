# -*- coding: utf-8 -*-
"""
    dnstamper
    *********

    This test resolves DNS for a list of domain names, one per line, in the
    file specified in the ooni-config under the setting "dns_experiment". If
    the file is top-1m.txt, the test will be run using Amazon's list of top
    one million domains. The experimental dns servers to query should
    be specified one per line in assets/dns_servers.txt.

    The test reports censorship if the cardinality of the intersection of
    the query result set from the control server and the query result set
    from the experimental server is zero, which is to say, if the two sets
    have no matching results whatsoever.

    NOTE: This test frequently results in false positives due to GeoIP-based
    load balancing on major global sites such as google, facebook, and
    youtube, etc.

    :author: Isis Lovecruft, Arturo Filastò
    :license: see LICENSE for more details

    TODO:
         * Finish porting to twisted
         * Finish the client.Resolver() subclass and test it
         * Use the DNS tests from captiveportal
         * Use plugoo/reports.py for final data
"""

import os

from twisted.names import client, dns
from twisted.internet import reactor, defer
from twisted.internet.error import CannotListenError
from twisted.internet.protocol import Factory, Protocol
from twisted.python import usage
from twisted.plugin import IPlugin
from zope.interface import implements

from ooni.plugoo.assets import Asset
from ooni.plugoo.tests import ITest, OONITest
from ooni import log

class AlexaAsset(Asset):
    """
    Class for parsing the Alexa top-1m.txt as an asset.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

    def parse_line(self, line):
        self = Asset.parse_line(self, line)
        return line.split(',')[1].replace('\n','')

class DNSTamperArgs(usage.Options):
    optParameters = [['hostnames', 'h', None, 
                      'Asset file of hostnames to resolve'],
                     ['controlresolver', 'c', '8.8.8.8', 
                      'Known good DNS server'],
                     ['testresolvers', 't', None, 
                      'Asset file of DNS servers to test'],
                     ['localresolvers', 'l', False, 
                      'Also test local servers'],
                     ['port', 'p', None, 
                      'Local UDP port to send queries over'],
                     ['usereverse', 'r', False, 
                      'Also try reverse DNS resolves'],
                     ['resume', 's', 0, 
                      'Resume at this index in the asset file']]

class DNSTamperResolver(client.Resolver):
    """
    Twisted by default issues DNS queries over cryptographically random
    UDP ports to mitigate the Berstein/Kaminsky attack on limited DNS
    Transaction ID numbers.[1][2][3]

    This is fine, unless the client has external restrictions which require
    DNS queries to be conducted over UDP port 53. Twisted does not provide
    an easy way to change this, ergo subclassing client.Resolver.[4] It 
    would perhaps be wise to patch twisted.names.client and request a merge
    into upstream.

    [1] https://twistedmatrix.com/trac/ticket/3342
    [2] http://blog.netherlabs.nl/articles/2008/07/09/ \
        some-thoughts-on-the-recent-dns-vulnerability
    [3] http://www.blackhat.com/presentations/bh-dc-09/Kaminsky/ \
        BlackHat-DC-09-Kaminsky-DNS-Critical-Infrastructure.pdf
    [4] http://comments.gmane.org/gmane.comp.python.twisted/22794
    """
    def __init__(self):
        super(DNSTamperResolver, self).__init__(self, resolv, servers,
                                                timeout, reactor)
        #client.Resolver.__init__(self)

        if self.local_options['port']:
            self.port = self.local_options['port']
        else:
            self.port = '53'

    def _connectedProtocol(self):
        """
        Return a new DNSDatagramProtocol bound to a specific port
        rather than the default cryptographically-random port.
        """
        if 'protocol' in self.__dict__:
            return self.protocol
        proto = dns.DNSDatagramProtocol(self)
        
        ## XXX We may need to remove the while loop, which was 
        ## originally implemented to safeguard against attempts to
        ## bind to the same random port twice...but then the code
        ## would be blocking...
        while True:
            try:
                self._reactor.listenUDP(self.port, proto)
            except error.CannotListenError:
                pass
            else:
                return proto

class DNSTamperTest(OONITest):
    """
    XXX fill me in
    """
    implements(IPlugin, ITest)

    shortName = "dnstamper"
    description = "DNS censorship detection test"
    requirements = None
    options = DNSTamperArgs
    blocking = False
    
    def __init__(self, local_options, global_options, 
                 report, ooninet=None, reactor=None):
        super(DNSTamperTest, self).__init__(local_options, global_options,
                                            report, ooninet, reactor)

    def __repr__(self):
        represent = "DNSTamperTest(OONITest): local_options=%r, " \
            "global_options=%r, assets=%r" % (self.local_options, 
                                              self.global_options, 
                                              self.assets)
        return represent

    def initialize(self):
        if self.local_options:
            ## client.createResolver() turns 'None' into '/etc/resolv.conf' on
            ## posix systems, ignored on Windows.
            if self.local_options['localresolvers']:
                self.resolvconf = None
            else:
                self.resolvconf = ''

    def load_assets(self):
        assets = {}

        default_hostnames = ['baidu.com', 'torrentz.eu', 'twitter.com', 
                             'ooni.nu', 'google.com', 'torproject.org']
        default_resolvers = ['209.244.0.3', '208.67.222.222']

        def asset_file(asset_option):
            return self.local_options[asset_option]

        def list_to_asset(list_):
            def next(list_):
                host = list_.pop()
                if host is not None:
                    yield str(host)
            while len(list_) > 0:
                next(list_)

        if self.local_options:
            if asset_file('hostnames'):
                with asset_file('hostnames') as hosts_file:
                    ## The default filename for the Alexa Top 1 Million:
                    if hosts_file is 'top-1m.txt':
                        assets.update({'hostnames': AlexaAsset(hosts_file)})
                    else:
                        assets.update({'hostnames': Asset(hosts_file)})
            else:
                log.msg("Error! We need an asset file containing the " + 
                        "hostnames that we should test DNS with! Please use " + 
                        "the '-h' option. Using pre-defined hostnames...")
                assets.update({'hostnames': list_to_asset(default_hostnames)})

            if asset_file('testresolvers'):
                with asset_file('testresolvers') as resolver_file:
                    assets.update({'testresolvers': Asset(resolver_file)})
            else:
                assets.update({'testresolvers': 
                               list_to_asset(default_resolvers)})

        return assets

    def lookup(self, hostname, resolver):
        """
        Resolves a hostname through a DNS nameserver to the corresponding IP
        addresses.
        """
        def got_result(result, hostname, resolver):
            ## XXX is there a report class that we should be using?
            log.msg('Resolved %s through %s to %s' 
                    % (hostname, resolver, result))
            outcome = {'resolved': True,
                       'domain': hostname,
                       'nameserver': resolver,
                       'address': result }
            log.msg(outcome)
            return result

        def got_error(err, hostname, resolver):
            log.msg(err.printTraceback())
            outcome = {'resolved': False,
                       'domain': hostname,
                       'nameserver': resolver,
                       'address': err }
            log.msg(outcome)
            return err

        res = client.createResolver(resolvconf=self.resolvconf, 
                                    servers=[(resolver, 53)])

        ## XXX should we do self.d.addCallback(resHostByName, hostname)?
        #d = res.getHostByName(hostname)
        #d.addCallbacks(got_result, got_error)

        #d = defer.Deferred()
        #d.addCallback(res.getHostByName, hostname)

        #d = res.getHostByName(hostname)
        #d.addCallback(got_result, result, hostname, resolver) 
        #d.addErrback(got_error, err, hostname, resolver)

        res.addCallback(getHostByName, hostname)
        res.addCallback(got_result, result, hostname, resolver)
        res.addErrback(got_error, err, hostname, resolver)

        if self.local_options['usereverse']:
            #d.addCallback(self.reverse_lookup, result, resolver)
            #d.addErrback(log.msg(err.printTraceback()))

            #d.addCallback(self.reverse_lookup, result, resolver)
            #d.addErrback(log.msg(err.printTraceback()))

            res.addCallback(self.reverse_lookup, result, resolver)
            res.addErraback(log.msg(err.printTraceback()))
        
        return res

    def reverse_lookup(self, address, resolver):
        """
        Attempt to do a reverse DNS lookup to determine if the control and exp
        sets from a positive result resolve to the same domain, in order to
        remove false positives due to GeoIP load balancing.
        """
        res = client.createResolver(resolvconf=self.resolvconf, 
                                    servers=[(resolver, 53)])
        ptr = '.'.join(addr.split('.')[::-1]) + '.in-addr.arpa'
        reverse = res.lookupPointer(ptr)
        reverse.addCallback(lambda (address, auth, add): 
                            util.println(address[0].payload.name))
        reverse.addErrback(log.err)

        ## XXX do we need to stop the reactor?
        #d.addBoth(lambda r: reactor.stop())

        return reverse
        
    def experiment(self, args):
        """
        Compares the lookup() sets of the control and experiment groups.
        """
        for hostname in args:
            for testresolver in self.assets['testresolvers']:
                addressd = defer.Deferred()
                addressd.addCallback(self.lookup, hostname, testresolver)
                addressd.addErrback(log.err)

                #addressd = self.lookup(hostname, testresolver)

                #self.d.addCallback(self.lookup, hostname, testserver)

                print "%s" % type(addressd)

                return addressd

    def control(self, experiment_result, args):
        print "EXPERIMENT RESULT IS %s" % experiment_result
        (exp_address, hostname, testserver, exp_reversed) = experiment_result
        control_server = self.local_options['controlserver']
        ctrl_address = self.lookup(hostname, control_server)
        
        ## XXX getHostByName() appears to be returning only one IP...

        if len(set(exp_address) & set(ctrl_address)) > 0:
            log.msg("Address %s has not tampered with on DNS server %s" 
                    % (hostname, test_server))
            return {'hostname': hostname,
                    'test-nameserver': test_server,
                    'test-address': exp_address,
                    'control-nameserver': control_server,
                    'control-address': ctrl_address,
                    'tampering-detected': False}
        else:
            log.msg("Address %s has possibly been tampered on %s:"
                    % (hostname, test_server))
            log.msg("DNS resolution through testserver %s yeilds: %s"
                    % (test_server, exp_address))
            log.msg("However, DNS resolution through controlserver %s yeilds: %s"
                    % (control_server, ctrl_address))

            if self.local_options['usereverse']:
                ctrl_reversed = self.reverse_lookup(experiment_result, control_server)
                if len(set(ctrl_reversed) & set(exp_reversed)) > 0:
                    log.msg("Further testing has eliminated false positives")
                else:
                    log.msg("Reverse DNS on the results returned by %s returned:"
                            % (test_server))
                    log.msg("%s" % exp_reversed)
                    log.msg("which does not match the expected domainname: %s"
                            % ctrl_reversed)
                return {'hostname': hostname,
                        'test-nameserver': test_server,
                        'test-address': exp_address,
                        'test-reversed': exp_reversed,
                        'control-nameserver': control_server,
                        'control-address': ctrl_address,
                        'control-reversed': ctrl_reversed,
                        'tampering-detected': True}
            else:
                return {'hostname': hostname,
                        'test-nameserver': test_server,
                        'test-address': exp_address,
                        'control-nameserver': control_server,
                        'control-address': ctrl_address,
                        'tampering-detected': False}

dnstamper = DNSTamperTest(None, None, None)

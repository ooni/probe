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
         * Use OONI log instead of print
         * Finish porting to twisted
         * Finish the client.Resolver() subclass and test it
         * Use the DNS tests from captiveportal
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
                     ['controlserver', 'c', '8.8.8.8', 
                      'Known good DNS server'],
                     ['testservers', 't', None, 
                      'Asset file of DNS servers to test'],
                     ['localservers', 'l', False, 
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
    implements(IPlugin, ITest)

    shortName = "dnstamper"
    description = "DNS censorship detection test"
    requirements = None
    options = DNSTamperArgs
    blocking = False

    #def __init__(self, local_options, global_options, 
    #             report, ooninet=None, reactor=None):
    #    super(DNSTamperTest, self).__init__(local_options, global_options,
    #                                        report, ooninet, reactor)
    #
    #    if self.reactor is None:
    #        self.reactor = reactor
    #
    #    if self.local_options:
    #        if self.local_options['localservers']:
    #        ## client.createResolver() turns None into '/etc/resolv.conf' 
    #        ## on posix systems, ignored on Windows.
    #            self.resolvconf = None
    #        else:
    #            self.resolvconf = ''

    def initialize(self):
        if self.local_options:

            ## client.createResolver() turns 'None' into '/etc/resolv.conf' on
            ## posix systems, ignored on Windows.
            if self.local_options['localservers']:
                self.resolvconf = None
            else:
                self.resolvconf = ''
        else:
            pass

        self.d = defer.Deferred()

    def load_assets(self):
        assets = {}

        if self.local_options:

            if self.local_options['hostnames']:
                assetf = self.local_options['hostnames']
                if assetf == 'top-1m.txt':
                    assets['hostnames'] = AlexaAsset(assetf)
                    #assets.update({'asset': AlexaAsset(assetf)})
                else:
                    assets['hostnames'] = Asset(assetf)
                    #assets.update({'asset': Asset(assetf)})
            else:
                #default_hostnames = ['google.com', 'torrentz.eu', 'ooni.nu', 
                #                     'twitter.com', 'baidu.com']
                #assets.update({'asset': [host for host in default_hostnames]})
                print "Error! We need a file containing the hostnames that we should test DNS for!"

            if self.local_options['testservers']:
                #assets['testservers'] = Asset(self.local_options['testservers'])
                self.testservers = Asset(self.local_options['testservers'])
            else:
                self.testservers = ['209.244.0.3', '208.67.222.222', '156.154.70.1']

        return assets

    def lookup(self, hostname, nameserver):
        """
        Resolves a hostname through a DNS nameserver to the corresponding
        IP addresses.
        """
        def got_result(result):
            log.msg('Resolved %s through %s to %s' 
                    % (hostname, nameserver, result))
            return {'resolved': True,
                    'domain': hostname,
                    'nameserver': nameserver,
                    'address': result}

        def got_error(err):
            log.msg(err.printTraceback())
            return {'resolved': False,
                    'domain': hostname,
                    'nameserver': nameserver,
                    'address': err}

        res = client.createResolver(resolvconf=self.resolvconf, 
                                    servers=[(nameserver, 53)])
        d = res.getHostByName(hostname)
        d.addCallbacks(got_result, got_error)
        
        return d

    def reverse_lookup(self, address, nameserver):
        """
        Attempt to do a reverse DNS lookup to determine if the control and exp
        sets from a positive result resolve to the same domain, in order to
        remove false positives due to GeoIP load balancing.
        """
        res = client.createResolver(resolvconf=self.resolvconf, 
                                    servers=[(nameserver, 53)])
        ptr = '.'.join(addr.split('.')[::-1]) + '.in-addr.arpa'
        d = res.lookupPointer(ptr)
        d.addCallback(lambda (ans, auth, add): util.println(ans[0].payload.name))
        d.addErrback(log.err)
        d.addBoth(lambda r: reactor.stop())
        return d
        
    def experiment(self, args):
        """
        Compares the lookup() sets of the control and experiment groups.
        """
        hostnames = args

        for hostname in hostnames:
            for testserver in self.testservers:
                #exp_address = self.lookup(hostname, testserver)
                self.d.addCallback(self.lookup, hostname, testserver)

        #print self.assets['hostnames']
        #hostname = args
        #exp_address = self.lookup(hostname, testserver)

        #return {'control': control_server,
        #        'domain': args['asset'],
        #        'experiment_address': address}

        if self.local_options['usereverse']:
            exp_reversed = self.reverse_lookup(exp_address, testserver)

            ## XXX trying to fix errors:
            #d = defer.Deferred()
            
            return (exp_address, hostname, testserver, exp_reversed)
        else:
            return (exp_address, hostname, testserver, False)

    def control(self, experiment_result):
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

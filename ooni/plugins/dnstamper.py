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

    :copyright: (c) 2012 Arturo Filastò, Isis Lovecruft
    :license: see LICENSE for more details

    TODO: 
    * Switch to using Twisted's DNS builtins instead of dnspython
    * 
"""

import os

from twisted.names import client
from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.python import usage
from twisted.plugin import IPlugin
from zope.interface import implements

from ooni.plugoo.assets import Asset
from ooni.plugoo.tests import ITest, OONITest
from ooni import log

class Top1MAsset(Asset):
    """
    Class for parsing the Alexa top-1m.txt as an asset.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

    def parse_line(self, line):
        self = Asset.parse_line(self, line)
        return line.split(',')[1].replace('\n','')

class DNSTamperArgs(usage.Options):
    optParameters = [['asset', 'a', None, 'Asset file of hostnames to resolve'],
                     ['controlserver', 'c', '8.8.8.8', 'Known good DNS server'],
                     ['testservers', 't', None, 'Asset file of DNS servers to test'],
                     ['usereverse', 'r', False, 'Also try reverse DNS resolves'],
                     ['resume', 's', 0, 'Resume at this index in the asset file']]

class DNSTamperTest(OONITest):
    implements(IPlugin, ITest)

    shortName = "dnstamper"
    description = "DNS censorship detection test"
    requirements = None
    options = DNSTamperArgs
    blocking = False
    
    def load_assets(self):
        assets = {}
        if self.local_options:
            if self.local_options['asset']:
                assetf = self.local_options['asset']
                if assetf == 'top-1m.txt':
                    assets.update({'asset': Top1MAsset(assetf)})
                else:
                    assets.update({'asset': Asset(assetf)})
            elif self.local_options['testservers']:
                assets.update({'testservers': 
                               Asset(self.local_options['testservers'])})
        return assets

    def lookup(self, hostname, nameserver):
        """
        Resolves a hostname through a DNS nameserver to the corresponding
        IP addresses.
        """
        def got_result(result):
            log.msg('Resolved %s through %s to %s' 
                    % (hostname, nameserver, result))
            reactor.stop()
            return {'resolved': True,
                    'domain': hostname,
                    'nameserver': nameserver,
                    'address': result}

        def got_error(err):
            log.msg(err.printTraceback())
            reactor.stop()
            return {'resolved': False,
                    'domain': hostname,
                    'nameserver': nameserver,
                    'address': err}

        res = client.createResolver(servers=[(nameserver, 53)])
        d = res.getHostByName(hostname)
        d.addCallbacks(got_result, got_error)
        return d

        ## XXX MAY ALSO BE:
        #answer = res.getAddress(servers=[('nameserver', 53)])

    def reverse_lookup(self, address, nameserver):
        """
        Attempt to do a reverse DNS lookup to determine if the control and exp
        sets from a positive result resolve to the same domain, in order to
        remove false positives due to GeoIP load balancing.
        """
        res = client.createResolver(servers=[(nameserver, 53)])
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
        test_server = self.local_options['testservers']
        hostname = args['asset']
        exp_address = self.lookup(hostname, test_server)

        #return {'control': control_server,
        #        'domain': args['asset'],
        #        'experiment_address': address}

        if self.local_options['usereverse']:
            exp_reversed = self.reverse_lookup(exp_address, test_server)
            return exp_address, hostname, test_server, exp_reversed
        else:
            return exp_address, hostname, test_server, False

    def control(self, experiment_result):
        (exp_address, hostname, test_server, exp_reversed) = experiment_result
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

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

class DNSTamperAsset(Asset):
    """
    Creates DNS testing specific Assets.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

class DNSTamperArgs(usage.Options):
    optParameters = [['asset', 'a', None, 'Asset file of hostnames to resolve'],
                     ['controlserver', 'c', '8.8.8.8', 'Known good DNS server'],
                     ['testservers', 't', None, 'Asset file of the DNS servers to test'],
                     ['resume', 'r', 0, 'Resume at this index in the asset file']]
'''
    def control(self, experiment_result, args):
        print "Experiment Result:", experiment_result
        print "Args", args
        return experiment_result

    def experiment(self, args):
'''        

class DNSTamperTest(OONITest):
    implements(IPlugin, ITest)

    shortName = "DNSTamper"
    description = "DNS censorship detection test"
    requirements = None
    options = DNSTamperArgs
    blocking = False
    
    def load_asset(self):
        if self.local_options:
            if self.local_options['asset']:
                assetf = self.local_options['asset']
                if assetf == 'top-1m.txt':
                    return {'asset': Top1MAsset(assetf)}
                else:
                    return {'asset': DNSTamperAsset(assetf)}
        else:
            return {}

    def lookup(self, hostname, nameserver):
        """
        Resolves a hostname through a DNS nameserver to the corresponding
        IP addresses.
        """
        res = client.createResolver(servers=[('nameserver', 53)])
        answer = res.getHostByName(hostname)
        ## XXX MAY ALSO BE:
        #answer = res.getAddress(servers=[('nameserver', 53)])

        ret = []

        for data in answer:
            ret.append(data.address)

        return ret

    def reverse_lookup(self, ip, nameserver):
        """
        Attempt to do a reverse DNS lookup to determine if the control and exp
        sets from a positive result resolve to the same domain, in order to
        remove false positives due to GeoIP load balancing.
        """
        res = client.createResolver(servers=nameserver)
        n = reversename.from_address(ip)
        revn = res.query(n, "PTR").__iter__().next().to_text()[:-1]

        return revn

    def experiment(self, *a, **kw):
        """
        Compares the lookup() sets of the control and experiment groups.
        """
        # this is just a dirty hack
        address = kw['data'][0]
        ns = kw['data'][1]

        config = self.config
        ctrl_ns = config.tests.dns_control_server

        print "ADDRESS: %s" % address
        print "NAMESERVER: %s" % ns

        exp = self.lookup(address, ns)
        control = self.lookup(address, ctrl_ns)

        result = []

        if len(set(exp) & set(control)) > 0:
            print "Address %s has not tampered with on DNS server %s\n" % (address, ns)
            result = (address, ns, exp, control, False)
            return result
        else:
            print "Address %s has possibly been tampered on %s:\nDNS resolution through %s yeilds:\n%s\nAlthough the control group DNS servers resolve to:\n%s" % (address, ns, ns, exp, control)
            result = (address, ns, exp, control, True)

            if config.tests.dns_reverse_lookup:

                exprevn = [self.reverse_lookup(ip, ns) for ip in exp]
                ctrlrevn = [self.reverse_lookup(ip, ctrl_ns)
                            for ip in control]

                if len(set(exprevn) & set(ctrlrevn)) > 0:
                    print "Further testing has eliminated this as a false positive."
                else:
                    print "Reverse DNS on the results returned by %s returned:\n%s\nWhich does not match the expected domainname:\n%s\n" % (ns, exprevn, ctrlrevn)
                return result

            else:
                print "\n"
                return result

#def run(ooni):
#    """
#    Run the test.
#    """
#    config = ooni.config
#    urls = []
#
#    if (config.tests.dns_experiment == "top-1m.txt"):
#        dns_experiment = Top1MAsset(os.path.join(config.main.assetdir,
#                                                 config.tests.dns_experiment))
#    else:
#        dns_experiment = DNSTAsset(os.path.join(config.main.assetdir,
#                                                config.tests.dns_experiment))
#    dns_experiment_dns = DNSTAsset(os.path.join(config.main.assetdir,
#                                                config.tests.dns_experiment_dns))
#
#    assets = [dns_experiment, dns_experiment_dns]
#
#    dnstest = DNST(ooni)
#    ooni.logger.info("Beginning dnstamper test...")
#    dnstest.run(assets, {'index': 1})
#    ooni.logger.info("Dnstamper test completed!")

dnstamper = DNSTamperTest(None, None, None)

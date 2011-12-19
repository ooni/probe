from dns import resolver
import gevent
import os
from plugoo import Plugoo, Asset

class DNSTAsset(Asset):
    def __init__(self, file=None):
        self = Asset.__init__(self, file)
    
    def next_asset(self):
        # Seriously... Rewrite it...
        if self.fh:
            line = self.fh.readline()
            if line:
                return line.replace('\n','')
            else:
                self.fh.seek(0)
                raise StopIteration
        else:
            raise StopIteration

class DNST(Plugoo):
    def lookup(self, hostname, ns):
        res = resolver.Resolver(configure=False)
        res.nameservers = [ns]
        answer = res.query(hostname)
        
        ret = []  
        
        for data in answer:
            ret.append(data.address)
        return ret
    
    def compare(self, *a, **kw):        
        # this is just a dirty hack
        address = kw['data'][0]
        ns = kw['data'][1]
        
        config = self.config
        
        print "ADDRESS: %s" % address
        print "NAMESERVER: %s" % ns
        
        exp = self.lookup(address, ns)
        control = self.lookup(address, config.tests.dns_control_server)
        
        if len(set(exp) & set(control)) > 0:
            print "%s : no tampering" % address
        else:
            print "%s : possible tampering (%s, %s)" % (exp, control)

def run(ooni):
    """Run the test
    """
    config = ooni.config
    urls = []
    
    dns_experiment = DNSTAsset(os.path.join(config.main.assetdir, config.tests.dns_experiment))
    dns_experiment_dns = DNSTAsset(os.path.join(config.main.assetdir, config.tests.dns_experiment_dns))

    assets = [dns_experiment, dns_experiment_dns]

    dnstest = DNST(config)
    ooni.logger.info("starting test")
    dnstest.run(assets)
    ooni.logger.info("finished")
    


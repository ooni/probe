from dns import resolver
import gevent
import os

def lookup(hostname, ns):
    res = resolver.Resolver(configure=False)
    res.nameservers = [ns]
    answer = res.query(hostname)
    
    ret = []  
    
    for data in answer:
        ret.append(data.address)
    return ret

def compare_lookups(args):
    # this is just a dirty hack
    address = args[0]
    ooni = args[1]
    ns = args[2]
    exp = lookup(address, ns)
    control = lookup(address, ooni.config.dns_control_server)
    print address
    if len(set(exp) & set(control)) > 0:
        print "No tampering"
    else:
        print "Tampering"
        print exp
        print control

def run(ooni):
    """Run the test
    """
    config = ooni.config
    urls = []
    
    f = open(os.path.join(config.main.assetdir, config.tests.dns_experiment))
    nsf = open(os.path.join(config.main.assetdir, config.tests.dns_experiment_dns))
    nss = [x.strip() for x in nsf.readlines()]
    i = 0
    # XXX Clean up this code
    ooni.logger.info("reading file")
    for url in f.readlines():
        jobs = [gevent.spawn(compare_lookups, (url, ooni, ns)) for ns in nss]
        gevent.joinall(jobs, timeout=2)
        [job.value for job in jobs]

    ooni.logger.info("finished")
    
    f.close()



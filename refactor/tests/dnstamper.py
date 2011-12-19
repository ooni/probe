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

def compare_lookups(address):
    exp = lookup(address, '8.8.8.8')
    control = lookup(address, '208.67.222.222')
    print address
    if len(set(exp) & set(control)) > 0:
        print "No tampering"
    else:
        print "Tampering"
        print exp
        print control

def run(ooni):
    config = ooni.config
    urls = []
    f = open(os.path.join(config.main.assetdir, config.tests.dns_experiment))
    i = 0
    ooni.logger.info("reading file")
    for line in f.readlines():
        urls.append(line.strip())
        if i % 100 == 0:
            jobs = [gevent.spawn(compare_lookups, url) for url in urls]
            gevent.joinall(jobs, timeout=2)
            [job.value for job in jobs]
            urls = []
    ooni.logger.info("finished")
    
    f.close()



import os
import time
import random
import re
from shutil import rmtree
from subprocess import Popen, PIPE

import plugoo
import gevent
from plugoo import Plugoo, Asset

class BridgeTAsset(Asset):
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

class BridgeT(Plugoo):    
    def writetorrc(self, bridge):
        # register Tor to an ephemeral port
        socksport = random.randint(49152, 65535)
        randomname = "tor_"+str(random.randint(0, 424242424242))
        datadir = "/tmp/" + randomname
        torrc = """SocksPort %s
UseBridges 1
bridge %s
DataDirectory %s
""" % (socksport, bridge, datadir)
        try:
            f = open(randomname, "wb")
            f.write(torrc)
        finally:
            f.close()
        
        os.mkdir(datadir)
        return (randomname, datadir)
    
    def connect(self, bridge, timeout=30):
        torrc, tordir = self.writetorrc(bridge)
        cmd = ["tor", "-f", torrc]
        
        tupdate = time.time()
        print "Doing popen"
        p = Popen(cmd, stdout=PIPE)
        
        while p:
            o = p.stdout.readline()
            if o == '' and p.poll() != None:
                os.unlink(os.path.join(os.getcwd(), torrc))
                rmtree(tordir)
                break

            if re.search("100%", o):
                print "%s bridge works" % bridge
                p.terminate()
                os.unlink(os.path.join(os.getcwd(), torrc))
                rmtree(tordir)
                return [bridge, True]
            
            if re.search("%", o):
                # Keep updating the timeout if there is progress
                tupdate = time.time()
                print o
            
            if time.time() - tupdate > timeout:
                print "%s bridge does not work (%s s timeout)" % (bridge, timeout)
                p.terminate()
                os.unlink(os.path.join(os.getcwd(), torrc))
                rmtree(tordir)
                return [bridge, True]

        os.unlink(os.path.join(os.getcwd(), torrc))
        rmtree(tordir)
                    
    def experiment(self, *a, **kw):
        # this is just a dirty hack
        bridge = kw['data']
        print "Experiment"
        config = self.config
        
        return self.connect(bridge)
        
def run(ooni):
    """Run the test
    """
    config = ooni.config
    urls = []
    
    bridges = BridgeTAsset(os.path.join(config.main.assetdir, \
                                            config.tests.tor_bridges))

    assets = [bridges]

    bridget = BridgeT(ooni)
    ooni.logger.info("starting test")
    bridget.run(assets)
    ooni.logger.info("finished")
    


import os
import sys
import errno
import time
import random
import re
from shutil import rmtree
from subprocess import Popen, PIPE

import plugoo
import gevent
from gevent import socket
import fcntl
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

    def connect(self, bridge, timeout=20):
        torrc, tordir = self.writetorrc(bridge)
        cmd = ["tor", "-f", torrc]

        tupdate = time.time()
        p = Popen(cmd, stdout=PIPE)
        # XXX this only works on UNIX (do we care?)
        # Make file reading non blocking
        fcntl.fcntl(p.stdout, fcntl.F_SETFL, os.O_NONBLOCK)

        while True:
            o = ""
            try:
                o = p.stdout.read(4096)
                if re.search("100%", o):
                    print "%s bridge works" % bridge
                    p.stdout.close()
                    os.unlink(os.path.join(os.getcwd(), torrc))
                    rmtree(tordir)
                    p.terminate()
                    return [bridge, True]

                if re.search("%", o):
                    # Keep updating the timeout if there is progress
                    tupdate = time.time()
                    print o
                    continue

            except IOError:
                ex = sys.exc_info()[1]
                if ex[0] != errno.EAGAIN:
                    raise
                sys.exc_clear()
            try:
                # Set the timeout for the socket wait
                ct = timeout-(time.time() - tupdate)
                socket.wait_read(p.stdout.fileno(), timeout=ct)
            except:
                print "%s bridge does not work (%s s timeout)" % (bridge, timeout)
                p.stdout.close()
                os.unlink(os.path.join(os.getcwd(), torrc))
                rmtree(tordir)
                p.terminate()
                return [bridge, False]

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



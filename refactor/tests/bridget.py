# -*- coding: UTF-8
"""
    bridgeT
    *******

    an OONI test (we call them Plugoos :P) aimed
    at detecting if a set of Tor bridges are working or not.

    :copyright: (c) 2012 by Arturo Filastò
    :license: BSD, see LICENSE for more details.
"""
import os
import sys
import errno
import time
import random
import re
from shutil import rmtree
from subprocess import Popen, PIPE
from datetime import datetime

import plugoo
import gevent
from gevent import socket
import fcntl
from plugoo import Plugoo, Asset, torify
import urllib2

try:
    from TorCtl import TorCtl
except:
    print "Error TorCtl not installed!"

class BridgeTAsset(Asset):
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

class BridgeT(Plugoo):
    # This is the timeout value after which
    # we will give up
    timeout = 20
    # These are the modules that should be torified
    modules = [urllib2]

    def writetorrc(self, bridge):
        # register Tor to an ephemeral port
        socksport = random.randint(49152, 65535)
        controlport = random.randint(49152, 65535)
        randomname = "tor_"+str(random.randint(0, 424242424242))
        datadir = "/tmp/" + randomname
        if bridge.startswith("obfs://"):
            obfsbridge = bridge.split("//")[1]
            torrc = """SocksPort %s
UseBridges 1
Bridge obfs2 %s
DataDirectory %s
ClientTransportPlugin obfs2 exec /usr/local/bin/obfsproxy --managed
ControlPort %s
""" % (socksport, obfsbridge, datadir, controlport)
        else:
            torrc = """SocksPort %s
UseBridges 1
bridge %s
DataDirectory %s
usemicrodescriptors 0
""" % (socksport, bridge, datadir)
        print torrc
        
        with open(randomname, "wb") as f:
            f.write(torrc)
        
        os.mkdir(datadir)
        return (randomname, datadir, controlport, socksport)

    def parsebridgeinfo(self, output):
        ret = {}
        fields = ['router', 'platform', 'opt', 'published', 'uptime', 'bandwidth']

        for x in output.split("\n"):
            cfield = x.split(' ')
            if cfield[0] in fields:
                ret[cfield[0]] = ' '.join(cfield[1:])
        return ret

    #Can't use @torify as it doesn't support concurrency right now 
    def download_file(self, socksport):
        socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, "127.0.0.1", int(socksport))
        socks.wrapmodule(urllib2)
        time_start=time.time()
        f = urllib2.urlopen('http://check.torproject.org')
        data= f.readlines()
        print data
        print len(data)
        time_end = time.time()
        print (time_end-time_start)
        return len(data)/(time_end-time_start)

    def connect(self, bridge, timeout=None):
        if not timeout:
            if self.config.tests.tor_bridges_timeout:
                self.timeout = self.config.tests.tor_bridges_timeout
            timeout = self.timeout
            #self.download_file()
        torrc, tordir, controlport, socksport = self.writetorrc(bridge)
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
                if o:
                    print o
                if re.search("100%", o):
                    print "%s bridge works" % bridge
                    print "%s controlport" % controlport
                    c = TorCtl.connect('127.0.0.1', controlport)
                    print c
                    #c.set_event_handler(LogHandler())
                    #c.set_events(["DEBUG", "INFO", "NOTICE", "WARN", "ERR"])
                    bridgeinfo = self.parsebridgeinfo(c.get_info('dir/server/all')['dir/server/all'])
                    #circID = c.extend_circuit(0, ["bridge","serenity"])
                    bandwidth=self.download_file(socksport)
                    print bandwidth
                    print c.get_info('stream-status')
                    #c.signal("HALT")
                    c.close()
                    p.stdout.close()
                    os.unlink(os.path.join(os.getcwd(), torrc))
                    rmtree(tordir)
                    p.terminate()
                    return {
                            'Time': datetime.now(),
                            'Bridge': bridge,
                            'Working': True,
                            'Descriptor': bridgeinfo,
                            'Calculated bandwidth': bandwidth
                            }

                if re.search("%", o):
                    # Keep updating the timeout if there is progress
                    tupdate = time.time()
                    #print o
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
                return {
                        'Time': datetime.now(),
                        'Bridge': bridge,
                        'Working': False,
                        'Descriptor': {}
                        }

    def experiment(self, *a, **kw):
        # this is just a dirty hack
        bridge = kw['data']
        print "Experiment"
        config = self.config

        return self.connect(bridge)

def run(ooni):
    """
    Run the test
    """
    config = ooni.config
    urls = []

    bridges = BridgeTAsset(os.path.join(config.main.assetdir, \
                                            config.tests.tor_bridges))

    assets = [bridges]

    bridget = BridgeT(ooni)
    ooni.logger.info("Starting bridget test")
    bridget.run(assets)
    ooni.logger.info("Testing completed!")



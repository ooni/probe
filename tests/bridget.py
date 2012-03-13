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
import glob
import socks
import socket
from shutil import rmtree
from subprocess import Popen, PIPE
from datetime import datetime

import shutil
import gevent
from gevent import socket
import fcntl
from plugoo.assets import Asset
from plugoo.tests import Test
import urllib2
import httplib
import json

try:
    from TorCtl import TorCtl
except:
    print "Error TorCtl not installed!"

__plugoo__ = "BridgeT"
__desc__ = "BridgeT, for testing Tor Bridge reachability"
ONIONOO_URL="http://85.214.195.203/summary/search/"

class SocksiPyConnection(httplib.HTTPConnection):
    def __init__(self, proxytype, proxyaddr, proxyport = None, rdns = True,
                 username = None, password = None, *args, **kwargs):
        self.proxyargs = (proxytype, proxyaddr, proxyport, rdns, username, password)
        httplib.HTTPConnection.__init__(self, *args, **kwargs)

    def connect(self):
        self.sock = socks.socksocket()
        self.sock.setproxy(*self.proxyargs)
        if isinstance(self.timeout, float):
            self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))

class SocksiPyHandler(urllib2.HTTPHandler):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kw = kwargs
        urllib2.HTTPHandler.__init__(self)

    def http_open(self, req):
        def build(host, port=None, strict=None, timeout=0):
            conn = SocksiPyConnection(*self.args, host=host, port=port,
                                      strict=strict, timeout=timeout, **self.kw)
            return conn
        return self.do_open(build, req)

class BridgeTAsset(Asset):
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

class BridgeT(Test):
    # This is the timeout value after which
    # we will give up
    timeout = 20
    # These are the modules that should be torified
    modules = [urllib2]

    def tor_greater_than(self, version):
        """
        Checks if the currently installed version of Tor is greater
        than the required version.

        :version The version of Tor to check against for greater than or equal
        """
        fullstring = os.popen("tor --version").read().split('\n')[-2]
        v_array = fullstring.split(' ')[2].split('-')
        minor = v_array[1:]
        v_array = v_array[0].split('.')
        minor_p = version.split('-')[1:]
        v_array_p = version.split('-')[0].split('.')

        for i, x in enumerate(v_array):
            try:
                if i > len(v_array_p):
                    break

                if int(x) > int(v_array_p[i]):
                    self.logger.debug("The Tor version is greater than %s" % version)
                    return True
                elif int(x) == int(v_array_p[i]):
                    self.logger.debug("The Tor version is greater than %s" % version)
                    continue
                else:
                    self.logger.debug("You run an outdated version of Tor: %s (< %s)" % (fullstring, version))
                    return False
            except:
                self.logger.error("Error in parsing your Tor version string: %s" % fullstring)
                return False

        self.logger.debug("The Tor version is equal to %s" % version)
        return True
        # XXX currently don't consider the minor parts of the version
        # (alpha, dev, beta, etc.)

    def free_port(self, port):
        s = socket.socket()
        try:
            s.bind(('127.0.0.1', port))
            s.close()
            return True
        except:
            self.logger.warn("The randomly chosen port was already taken!")
            s.close()
            return False

    def writetorrc(self, bridge):
        """
        Write the torrc file for the tor process to be used
        to test the bridge.

        :bridge the bridge to be tested
        """
        self.failures = []
        prange = (49152, 65535)

        # register Tor to an ephemeral port
        socksport = random.randint(prange[0], prange[1])
        # Keep on trying to get a new port if the chosen one is already
        # taken.
        while not self.free_port(socksport):
            socksport = random.randint(prange[0], prange[1])
        controlport = random.randint(prange[0], prange[1])
        while not self.free_port(controlport):
            controlport = random.randint(prange[0], prange[1])

        randomname = "tor_"+str(random.randint(0, 424242424242))
        datadir = "/tmp/" + randomname
        if bridge.startswith("obfs://"):
            obfsbridge = bridge.split("//")[1]

            self.logger.debug("Genearting torrc file for obfs bridge")
            torrc = """SocksPort %s
UseBridges 1
Bridge obfs2 %s
DataDirectory %s
ClientTransportPlugin obfs2 exec /usr/local/bin/obfsproxy --managed
ControlPort %s
Log info file %s
""" % (socksport, obfsbridge, datadir, controlport, os.path.join(datadir,'tor.log'))
        else:
            self.logger.debug("Generating torrc file for bridge")
            if self.tor_greater_than('0.2.3.2'):

                torrc = """SocksPort %s
UseBridges 1
bridge %s
DataDirectory %s
usemicrodescriptors 0
ControlPort %s
Log info file %s
""" % (socksport, bridge, datadir, controlport, os.path.join(datadir,'tor.log'))
            else:
                torrc = """SocksPort %s
UseBridges 1
bridge %s
DataDirectory %s
ControlPort %s
Log info file %s
""" % (socksport, bridge, datadir, controlport, os.path.join(datadir,'tor.log'))

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
                #not sure if hellais did this on purpose, but this overwrites
                #the previous entries. For ex, 'opt' has multiple entries and
                #only the last value is stored
                ret[cfield[0]] = ' '.join(cfield[1:])
                if cfield[1] == 'fingerprint':
                    ret['fingerprint'] = ''.join(cfield[2:])
        return ret

    #Can't use @torify as it doesn't support concurrency right now
    def download_file(self, socksport):
        opener = urllib2.build_opener(SocksiPyHandler(socks.PROXY_TYPE_SOCKS5,
                                                      '127.0.0.1', int(socksport)))

        time_start=time.time()
        f = opener.open('http://38.229.72.16/bwauth.torproject.org/256k')
        f.read()
        time_end = time.time()
        print (time_end-time_start)
        return str(256/(time_end-time_start)) + " KB/s"

    def is_public(self, fp, socksport):
        opener = urllib2.build_opener(SocksiPyHandler(socks.PROXY_TYPE_SOCKS5,'127.0.0.1',int(socksport)))
        response = opener.open(str(ONIONOO_URL)+str(fp))
        reply = json.loads(response.read())
        if reply['bridges'] or reply['relays']:
            return True
        return False

    def connect(self, bridge, timeout=None):
        bridgeinfo = None
        bandwidth = None
        public = None
        if not timeout:
            if self.config.tests.tor_bridges_timeout:
                self.timeout = self.config.tests.tor_bridges_timeout
            timeout = self.timeout
        torrc, tordir, controlport, socksport = self.writetorrc(bridge)
        cmd = ["tor", "-f", torrc]

        tupdate = time.time()
        debugupdate = time.time()

        try:
            p = Popen(cmd, stdout=PIPE)
        except:
            self.logger.error("Error in starting Tor (do you have tor installed?)")

        # XXX this only works on UNIX (do we care?)
        # Make file reading non blocking
        try:
            fcntl.fcntl(p.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        except:
            self.logger.error("Unable to set file descriptor to non blocking")

        self.logger.info("Testing bridge: %s" % bridge)
        while True:
            o = ""
            try:
                o = p.stdout.read(4096)
                if o:
                    self.logger.debug(str(o))
                if re.search("100%", o):
                    self.logger.info("Success in connecting to %s" % bridge)

                    print "%s bridge works" % bridge
                    # print "%s controlport" % controlport
                    try:
                        c = TorCtl.connect('127.0.0.1', controlport)
                        bridgeinfo = self.parsebridgeinfo(c.get_info('dir/server/all')['dir/server/all'])
                        c.close()
                    except:
                        self.logger.error("Error in connecting to Tor Control port")

                    # XXX disable the public checking
                    #public = self.is_public(bridgeinfo['fingerprint'], socksport)
                    #self.logger.info("Public: %s" % public)

                    bandwidth = self.download_file(socksport)
                    self.logger.info("Bandwidth: %s" % bandwidth)

                    try:
                        p.stdout.close()
                    except:
                        self.logger.error("Error in closing stdout FD.")

                    try:
                        os.unlink(os.path.join(os.getcwd(), torrc))
                        rmtree(tordir)
                    except:
                        self.logger.error("Error in unlinking files.")

                    p.terminate()
                    return {
                            'Time': datetime.now(),
                            'Bridge': bridge,
                            'Working': True,
                            'Descriptor': bridgeinfo,
                            'Calculated bandwidth': bandwidth,
                            'Public': public
                            }

                if re.search("%", o):
                    # Keep updating the timeout if there is progress
                    self.logger.debug("Updating time...")
                    tupdate = time.time()
                    #print o
                    continue

            except IOError:
                ex = sys.exc_info()[1]
                if ex[0] != errno.EAGAIN:
                    self.logger.error("Error IOError: EAGAIN")
                    raise
                sys.exc_clear()

            try:
                # Set the timeout for the socket wait
                ct = timeout-(time.time() - tupdate)
                socket.wait_read(p.stdout.fileno(), timeout=ct)

            except:
                lfh = open(os.path.join(tordir, 'tor.log'), 'r')
                log = lfh.readlines()
                lfh.close()
                self.logger.info("%s bridge does not work (%s s timeout)" % (bridge, timeout))
                print "%s bridge does not work (%s s timeout)" % (bridge, timeout)
                self.failures.append(bridge)
                p.stdout.close()
                os.unlink(os.path.join(os.getcwd(), torrc))
                rmtree(tordir)
                p.terminate()
                return {
                        'Time': datetime.now(),
                        'Bridge': bridge,
                        'Working': False,
                        'Descriptor': {},
                        'Log': log
                        }

    def experiment(self, *a, **kw):
        # this is just a dirty hack
        bridge = kw['data']
        print "Experiment"
        config = self.config

        return self.connect(bridge)

    def clean(self):
        for infile in glob.glob('tor_*'):
            os.remove(infile)

    def print_failures(self):
        if self.failures:
            for item in self.failures:
                print "Offline : %s" % item
        else:
            print "All online"

    # For logging TorCtl event msgs
    #class LogHandler:
    #def msg(self, severity, message):
    #   print "[%s] %s"%(severity, message)

def run(ooni, assets=None):
    """
    Run the test
    """

    config = ooni.config
    urls = []

    bridges = BridgeTAsset(os.path.join(config.main.assetdir, \
                                        config.tests.tor_bridges))

    bridgelist = [bridges]

    bridget = BridgeT(ooni)
    ooni.logger.info("Starting bridget test")
    bridget.run(bridgelist)
    bridget.print_failures()
    bridget.clean()
    ooni.logger.info("Testing completed!")

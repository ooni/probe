#!/usr/bin/python
# Copyright 2009 The Tor Project, Inc.
# License at end of file.
#
# This tests connections to a list of Tor nodes in a given Tor consensus file
# while also recording the certificates - it's not a perfect tool but complete
# or even partial failure should raise alarms.
#
# This plugoo uses threads and as a result, it's not friendly to SIGINT signals.
#

import logging
import socket
import time
import random
import threading
import sys
import os

from ooni.plugooni import Plugoo
from ooni.common import Storage

ssl = OpenSSL = None

try:
    import ssl
except ImportError:
    pass

if ssl is None:
    try:
        import OpenSSL.SSL
        import OpenSSL.crypto
    except ImportError:
        pass

if ssl is None and OpenSSL is None:
    if socket.ssl:
        print """Your Python is too old to have the ssl module, and you haven't
installed pyOpenSSL.  I'll try to work with what you've got, but I can't
record certificates so well."""
    else:
        print """Your Python has no OpenSSL support.  Upgrade to 2.6, install
pyOpenSSL, or both."""
        sys.exit(1)

################################################################

# How many servers should we test in parallel?
N_THREADS = 16

# Where do we write the results?
OUTPUT = "results/marco.out"

# Where do we write certificates?
CERT_OUTPUT = "results/marco_certs.out"

# Where do we log the result of the run.
LOGFILE = "results/marco.log"

# How long do we give individual socket operations to succeed or fail?
# (Seconds)
TIMEOUT = 10

################################################################

CONNECTING = "noconnect"
HANDSHAKING = "nohandshake"
OK = "ok"
ERROR = "err"

LOCK = threading.RLock()
socket.setdefaulttimeout(TIMEOUT)

def clean_pem_cert(cert):
    idx = cert.find('-----END')
    if idx > 1 and cert[idx-1] != '\n':
        cert = cert.replace('-----END','\n-----END')
    return cert

def record((addr,port), state, extra=None, cert=None):
    LOCK.acquire()
    try:
        print >>OUT, "%s:%d %s %r" %(addr,port,state,extra)
        OUT.flush()
        if cert:
            print >>CERT_OUT, "%s:%d\n%s"%(addr,port,clean_pem_cert(cert))
            CERT_OUT.flush()
    finally:
        LOCK.release()

def probe(address,theCtx=None):
    sock = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logging.info("Opening socket to %s",address)
    try:
        s.connect(address)
    except IOError, e:
        logging.info("Error %s from socket connect.",e)
        record(address, CONNECTING, e)
        s.close()
        return
    logging.info("Socket to %s open.  Launching SSL handshake.",address)
    if ssl:
        try:
            s = ssl.wrap_socket(s,cert_reqs=ssl.CERT_NONE,ca_certs=None)
            # "MARCO!"
            s.do_handshake()
        except IOError, e:
            logging.info("Error %s from ssl handshake",e)
            record(address, HANDSHAKING, e)
            s.close()
            sock.close()
            return
        cert = s.getpeercert(True)
        if cert != None:
            cert = ssl.DER_cert_to_PEM_cert(cert)
    elif OpenSSL:
        try:
            s = OpenSSL.SSL.Connection(theCtx, s)
            s.set_connect_state()
            s.setblocking(True)
            s.do_handshake()
            cert = s.get_peer_certificate()
            if cert != None:
                cert = OpenSSL.crypto.dump_certificate(
                    OpenSSL.crypto.FILETYPE_PEM, cert)
        except IOError, e:
            logging.info("Error %s from OpenSSL handshake",e)
            record(address, HANDSHAKING, e)
            s.close()
            sock.close()
            return
    else:
        try:
            s = socket.ssl(s)
            s.write('a')
            cert = s.server()
        except IOError, e:
            logging.info("Error %s from socket.ssl handshake",e)
            record(address, HANDSHAKING, e)
            sock.close()
            return

    logging.info("SSL handshake with %s finished",address)
    # "POLO!"
    record(address,OK, cert=cert)
    if (ssl or OpenSSL):
        s.close()
    sock.close()

def parseNetworkstatus(ns):
    for line in ns:
        if line.startswith('r '):
            r = line.split()
            yield (r[-3],int(r[-2]))

def parseCachedDescs(cd):
    for line in cd:
        if line.startswith('router '):
            r = line.split()
            yield (r[2],int(r[3]))

def worker(addrList, origLength):
    done = False
    logging.info("Launching thread.")

    if OpenSSL is not None:
        context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    else:
        context = None

    while True:
        LOCK.acquire()
        try:
            if addrList:
                print "Starting test %d/%d"%(
                    1+origLength-len(addrList),origLength)
                addr = addrList.pop()
            else:
                return
        finally:
            LOCK.release()

        try:
            logging.info("Launching probe for %s",addr)
            probe(addr, context)
        except Exception, e:
            logging.info("Unexpected error from %s",addr)
            record(addr, ERROR, e)

def runThreaded(addrList, nThreads):
    ts = []
    origLen = len(addrList)
    for num in xrange(nThreads):
        t = threading.Thread(target=worker, args=(addrList,origLen))
        t.setName("Th#%s"%num)
        ts.append(t)
        t.start()
    for t in ts:
        logging.info("Joining thread %s",t.getName())
        t.join()

def main(self, args):
    global OUT
    global CERT_OUT

    try:
        OUT = open(args.output.main, 'w')
    except:
        print "No output file given. quitting..."
        return -1

    try:
        CERT_OUT = open(args.output.certificates, 'w')
    except:
        print "No output cert file given. quitting..."
        return -1

    logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
                        datefmt="%b %d %H:%M:%S",
                        level=logging.INFO,
                        filename=args.log)
    logging.info("============== STARTING NEW LOG")
    if ssl is not None:
        methodName = "ssl"
    elif OpenSSL is not None:
        methodName = "OpenSSL"
    else:
        methodName = "socket"
    logging.info("Running marco with method '%s'", methodName)

    addresses = set()

    if args.input.ips:
        for fn in input.file(args.input.ips).simple():
            addresses.add( (a,b) )

    elif args.input.consensus:
        for fn in args:
            print fn
            for a,b in parseNetworkstatus(open(args.input.consensus)):
                addresses.add( (a,b) )

    if len(addresses) == 0:
        logging.error("No input source given, quiting...")
        return -1

    addresses = list(addresses)
    addresses.sort()

    runThreaded(addresses, N_THREADS)

class MarcoPlugin(Plugoo):
  def __init__(self):
    self.name = ""

    self.modules = [ "logging", "socket", "time", "random", "threading", "sys",
                     "OpenSSL.SSL", "OpenSSL.crypto", "os" ]

    self.input = Storage()
    self.input.ip = None
    self.input.consensus = os.path.expanduser("~/.tor/cached-consensus")

    self.output = Storage()
    self.output.main = 'reports/marco.out'
    self.output.certificates = 'reports/marco_certs.out'

    # We require for Tor to already be running or have recently run
    self.args = Storage()
    self.args.input = self.input
    self.args.output = self.output
    self.args.log = 'reports/marco.log'

  def ooni_main(self, cmd):
    main(self, self.args)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print >> sys.stderr, ("This script takes one or more networkstatus "
                              "files as an argument.")
    self = None
    main(self, sys.argv[1:])

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
# copyright notice, this list of conditions and the following disclaimer
# in the documentation and/or other materials provided with the
# distribution.
#
#     * Neither the names of the copyright owners nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

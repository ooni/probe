#!/usr/bin/python
# Copyright 2011 The Tor Project, Inc.
# License at end of file.
#
# This is a modified version of the marco plugoo. Given a list of #
# IP:port addresses, this plugoo will attempt a TCP connection with each
# host and write the results to a .yamlooni file.
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
try:
    from ooni.plugooni import Plugoo
except:
    print "Error importing Plugoo"

try:
    from ooni.common import Storage
except:
    print "Error importing Storage"

try:
    from ooni import output
except:
    print "Error importing output"

try:
    from ooni import input
except:
    print "Error importing output"

################################################################

# How many servers should we test in parallel?
N_THREADS = 16

# How long do we give individual socket operations to succeed or fail?
# (Seconds)
TIMEOUT = 10

################################################################

CONNECTING = "noconnect"
OK = "ok"
ERROR = "err"

LOCK = threading.RLock()
socket.setdefaulttimeout(TIMEOUT)

# We will want to log the IP address, the port and the state
def record((addr,port), state, extra=None):
    LOCK.acquire()
    try:
        OUT.append({'addr' : addr,
                    'port' : port,
                    'state' : state,
                    'extra' : extra})
    finally:
        LOCK.release()

# For each IP address in the list, open a socket, write to the log and
# then close the socket
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
    logging.info("Socket to %s open.  Successfully launched TCP handshake.",address)
    record(address, OK)
    s.close()

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
        t.join()

def main(self, args):
    # BEGIN
    # This logic should be present in more or less all plugoos
    global OUT
    global OUT_DATA
    OUT_DATA = []

    try:
        OUT = output.data(name=args.output.main) #open(args.output.main, 'w')
    except:
        print "No output file given. quitting..."
        return -1

    logging.basicConfig(format='%(asctime)s [%(levelname)s] [%(threadName)s] %(message)s',
                        datefmt="%b %d %H:%M:%S",
                        level=logging.INFO,
                        filename=args.log)
    logging.info("============== STARTING NEW LOG")
    # END

    methodName = "socket"
    logging.info("Running tcpcon with method '%s'", methodName)

    addresses = []

    if args.input.ips:
        for fn in input.file(args.input.ips).simple():
            a, b = fn.split(":")
            addresses.append( (a,int(b)) )

    elif args.input.consensus:
        for fn in args:
            print fn
            for a,b in parseNetworkstatus(open(args.input.consensus)):
                addresses.append( (a,b) )

    if args.input.randomize:
        # Take a random permutation of the set the knuth way!
        for i in range(0, len(addresses)):
            j = random.randint(0, i)
            addresses[i], addresses[j] = addresses[j], addresses[i]

    if len(addresses) == 0:
        logging.error("No input source given, quiting...")
        return -1

    addresses = list(addresses)

    if not args.input.randomize:
        addresses.sort()

    runThreaded(addresses, N_THREADS)

class MarcoPlugin(Plugoo):
  def __init__(self):
    self.name = ""

    self.modules = [ "logging", "socket", "time", "random", "threading", "sys",
                     "os" ]

    self.input = Storage()
    self.input.ip = None
    try:
        c_file = os.path.expanduser("~/.tor/cached-consensus")
        open(c_file)
        self.input.consensus = c_file
    except:
        pass

    try:
        c_file = os.path.expanduser("~/tor/bundle/tor-browser_en-US/Data/Tor/cached-consensus")
        open(c_file)
        self.input.consensus = c_file
    except:
        pass

    if not self.input.consensus:
        print "Error importing consensus file"
        sys.exit(1)

    self.output = Storage()
    self.output.main = 'reports/tcpcon-1.yamlooni'
    self.output.certificates = 'reports/tcpcon_certs-1.out'

    # XXX This needs to be moved to a proper function
    #     refactor, refactor and ... refactor!
    if os.path.exists(self.output.main):
        basedir = "/".join(self.output.main.split("/")[:-1])
        fn = self.output.main.split("/")[-1].split(".")
        ext = fn[1]
        name = fn[0].split("-")[0]
        i = fn[0].split("-")[1]
        i = int(i) + 1
        self.output.main = os.path.join(basedir, name + "-" + str(i) + "." + ext)

    if os.path.exists(self.output.certificates):
        basedir = "/".join(self.output.certificates.split("/")[:-1])
        fn = self.output.certificates.split("/")[-1].split(".")
        ext = fn[1]
        name = fn[0].split("-")[0]
        i = fn[0].split("-")[1]
        i = int(i) + 1
        self.output.certificates= os.path.join(basedir, name + "-" + str(i) + "." + ext)

    # We require for Tor to already be running or have recently run
    self.args = Storage()
    self.args.input = self.input
    self.args.output = self.output
    self.args.log = 'reports/tcpcon.log'

  def ooni_main(self, cmd):
    self.args.input.randomize = cmd.randomize
    self.args.input.ips = cmd.listfile
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

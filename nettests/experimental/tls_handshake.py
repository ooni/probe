#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
  tls_handshake.py
  ----------------
  This file contains test cases for determining if a TLS handshake completes
  successfully, including ways to test if a TLS handshake which uses Mozilla
  Firefox's current ciphersuite list completes.

  These NetTestCases are a rewrite of a script contributed by Hackerberry
  Finn, in order to fit into OONI's core network tests.

  @authors: Isis Agora Lovecruft <isis@torproject.org>,
            Hackerberry Finn <anon@localhost>
  @license: see included LICENSE file
"""

import os
import socket
from socket import error as serror
import struct
import sys

from ipaddr import IPAddress
from OpenSSL import SSL
from twisted.internet import defer
from twisted.python import usage

from ooni import nettest, config
from ooni.utils import log

## For a way to obtain the current version of Firefox's default ciphersuite
## list, see https://trac.torproject.org/projects/tor/attachment/ticket/4744/
## and the attached file "get_mozilla_files.py".
##
## Note, however, that doing so requires the source code to the version of
## firefox that you wish to emulate.

firefox_ciphers = ["ECDHE-ECDSA-AES256-SHA",
                   "ECDHE-RSA-AES256-SHA",
                   "DHE-RSA-CAMELLIA256-SHA",
                   "DHE-DSS-CAMELLIA256-SHA",
                   "DHE-RSA-AES256-SHA",
                   "DHE-DSS-AES256-SHA",
                   "ECDH-ECDSA-AES256-CBC-SHA",
                   "ECDH-RSA-AES256-CBC-SHA",
                   "CAMELLIA256-SHA",
                   "AES256-SHA",
                   "ECDHE-ECDSA-RC4-SHA",
                   "ECDHE-ECDSA-AES128-SHA",
                   "ECDHE-RSA-RC4-SHA",
                   "ECDHE-RSA-AES128-SHA",
                   "DHE-RSA-CAMELLIA128-SHA",
                   "DHE-DSS-CAMELLIA128-SHA",]


class NoSSLContextError(Exception):
    """
    Raised when we're missing the SSL context method, which should be one of
    the following:

        * :attr:`OpenSSL.SSL.SSLv2_METHOD`
        * :attr:`OpenSSL.SSL.SSLv23_METHOD`
        * :attr:`OpenSSL.SSL.SSLv3_METHOD`
        * :attr:`OpenSSL.SSL.TLSv1_METHOD`
    """
    pass

class HostUnreachableError(Exception):
    """Raised when there the host IP address appears to be unreachable."""
    pass

class UsageOptions(usage.Options):
    optParameters = [
        ['host', 'h', None, 'Remote host IP address (v4/v6)'],
        ['port', 'p', None,
         "Use this port for all hosts, regardless of port specified in file"],
        ['ciphersuite', 'c', None ,
         'File containing ciphersuite list, one per line'],]
    optFlags = [
        ['ssl2', '2', 'Use SSLv2'],
        ['ssl3', '3', 'Use SSLv3'],
        ['tls1', 't', 'Use TLSv1'],]

class TLSHandshakeTest(nettest.NetTestCase):
    """
    An ooniprobe NetTestCase for determining if we can complete a TLS handshake
    with a remote host.
    """
    name         = 'tls-handshake'
    author       = 'Isis Lovecruft <isis@torproject.org>'
    description  = 'A test to determing if we can complete a TLS hankshake.'
    version      = '0.0.1'

    requiresRoot = False
    usageOptions = UsageOptions

    inputFile = ['file', 'f', None, 'List of <IP>:<PORT>s to test']

    def setUp(self, *args, **kwargs):
        if self.localOptions:
            options = self.localOptions
            self.ciphers = []
            self.methods = []

            ## check that we're actually testing an IP:PORT, else exit
            ## gracefully:
            if not (options['host'] and options['port']) \
                    and not options['file']:
                 sys.exit("Need --host and --port, or --file!")

            ## set the SSL/TLS method to use:
            for method in ['ssl2', 'ssl3', 'tls1']:
                if options[method]:
                    self.methods.append(method)

            ## if we weren't given a file with a list of ciphersuites to use,
            ## then use the firefox default list:
            if not options['ciphersuite']:
                self.ciphers = firefox_ciphers
            else:
                if os.path.isfile(options['ciphersuite']):
                    with open(options['ciphersuite']) as cipherfile:
                        for line in cipherfile.readlines():
                            self.ciphers.append(line.strip())
            self.ciphersuite = ":".join(self.ciphers)

        if hasattr(config.advanced, 'default_timeout'):
            timeout = config.advanced.default_timeout
        else:
            timeout = 10   ## default the timeout to 10 seconds
        socket.setdefaulttimeout(timeout)
        self.timeout = struct.pack('ll', int(timeout), 0)

    def splitInput(self, input):
        addr, port = input.strip().rsplit(':', 1)
        if self.localOptions['port']:
            port = self.localOptions['port']
        return (str(addr), int(port))

    def inputProcessor(self, file=None):
        if os.path.isfile(file):
            with open(file) as fh:
                for line in fh.readlines():
                    if line.startswith('#'):
                        continue
                    yield self.splitInput(line)

    def buildSocket(self, addr):
        ip = IPAddress(addr) ## learn if we're IPv4 or IPv6
        if ip.version == 4:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif ip.version == 6:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        return s

    def getContext(self):
        if 'ssl2' in self.methods:
            if not 'ssl3' in self.methods:
                context = SSL.Context(SSL.SSLv2_METHOD)
            else:
                context = SSL.Context(SSL.SSLv23_METHOD)
        elif 'ssl3' in self.methods:
            context = SSL.Context(SSL.SSLv3_METHOD)
        elif 'tls1' in self.methods:
            context = SSL.Context(SSL.TLSv1_METHOD)
        else:
            raise Exception("No SSL/TLS method chosen!")
        context.set_cipher_list(self.ciphersuite)
        return context

    def test_tlsv1_handshake(self):

        def makeConnection(addr, port):
            socket = self.buildSocket(addr)
            context = self.getContext()

            connection = SSL.Connection(context, socket)

            try:
                connection.connect((addr, port))
            except serror, se:
                if se.message.find("[Errno 101]"):
                    connection.shutdown()
                log.err(se)
            else:
                connection.setblocking(1)
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO,
                                      self.timeout)
                log.msg("Connected to %s" % connection.getpeername())
                log.msg("Connection state: %s " % connection.state_string())
            return connection

        def doHandshake(connection):
            try:
                connection.do_handshake()
            except SSL.WantReadError():
                log.msg("Timeout exceeded.")
                connection.shutdown()
            else:
                log.msg("State: %s" % connection.state_string())
                log.msg("Transmitted %d bytes" % connection.send("o\r\n"))
                try:
                    recvstr = connection.recv(1024)
                except SSL.WantReadError:
                    log.msg("Timeout exceeded")
                    connection.shutdown()
                else:
                    log.msg("Received: %s" % recvstr)
            return connection

        def handshakeSucceeded(connection):
            if connection:
                host, port = connection.getpeername()
                self.report['host'] = host
                self.report['port'] = port
                self.report['state'] = connection.state_string()

        def handshakeFailed(connection, addr, port):
            if connection is None:
                self.report['host'] = addr
                self.report['port'] = port
                self.report['state'] = 'FAILED'
            else:
                return handshakeSucceeded(connection)

        addr, port = self.input
        connection = defer.maybeDeferred(makeConnection, addr, port)
        connection.addCallback(doHandshake)
        connection.addErrback(log.err)
        connection.addCallback(handshakeSucceeded)
        connection.addErrback(handshakeFailed)

        return connection

## XXX clean me up
## old function from anonymous contribution: (saved mostly for reference of the
## success string)
##
#def checkBridgeConnection(host, port)
#  cipher_arg = ":".join(ciphers)
#  cmd  = ["openssl", "s_client", "-connect", "%s:%s" % (host,port)]
#  cmd += ["-cipher", cipher_arg]
#  proc = subprocess.Popen(cmd, stdout=PIPE, stderr=PIPE,stdin=PIPE)
#  out, error = proc.communicate()
#  success = "Cipher is DHE-RSA-AES256-SHA" in out
#  return success

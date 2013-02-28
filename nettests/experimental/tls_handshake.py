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

            ## check that we're testing an IP:PORT, else exit gracefully:
            if not ((options['host'] and options['port']) or options['file']):
                 sys.exit("Need --host and --port, or --file!")

            ## xxx TODO there's nothing that tells the user they can only have
            ##     one of the TLS/SSL methods at a time.

            ## set the SSL/TLS method to use:
            if options['ssl2']:
                if not options['ssl3']:
                    self.context = SSL.Context(SSL.SSLv2_METHOD)
                else:
                    self.context = SSL.Context(SSL.SSLv23_METHOD)
            elif options['ssl3']:
                self.context = SSL.Context(SSL.SSLv3_METHOD)
            elif options['tls1']:
                self.context = SSL.Context(SSL.TLSv1_METHOD)
            else:
                try:
                    raise NoSSLContextError(
                        "No SSL/TLS context chosen! Defaulting to TLSv1...")
                except NoSSLContextError, ncse:
                    log.err(ncse.message)
                    self.context = SSL.Context(SSL.TLSv1_METHOD)

            if not options['ciphersuite']:
                self.ciphers = firefox_ciphers
            else:
                ## if we weren't given a file with a list of ciphersuites to
                ## use, then use the firefox default list:
                if os.path.isfile(options['ciphersuite']):
                    with open(options['ciphersuite']) as cipherfile:
                        for line in cipherfile.readlines():
                            self.ciphers.append(line.strip())
            self.ciphersuite = ":".join(self.ciphers)

        if getattr(config.advanced, 'default_timeout', None) is not None:
            self.timeout = config.advanced.default_timeout
        else:
            self.timeout = 30   ## default the timeout to 30 seconds

        ## xxx For debugging, set the socket timeout higher anyway:
        self.timeout = 30

        ## We have to set the default timeout on our sockets before creation:
        socket.setdefaulttimeout(self.timeout)

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
        self.context.set_cipher_list(self.ciphersuite)
        return self.context

    @staticmethod
    def getPeerCert(connection, get_chain=False):
        if not get_chain:
            x509_cert = connection.get_peer_certificate()
            pem_cert = dump_certificate(FILETYPE_PEM, x509_cert)
            return pem_cert
        else:
            cert_chain = []
            x509_cert_chain = connection.get_peer_cert_chain()
            for x509_cert in x509_cert_chain:
                pem_cert = dump_certificate(FILETYPE_PEM, x509_cert)
                cert_chain.append(pem_cert)
            return cert_chain

    def test_tlsv1_handshake(self):
        """xxx fill me in"""

        def makeConnection(host):
            """
            Create a socket to the host's IP address, then get the TLS/SSL context
            method and ciphersuite list. Lastly, initiate a connection to the
            host.

            @param host: A tuple of the host IP and port, i.e. (addr, port).
            @returns: A :class:`OpenSSL.SSL.Connection` object (or any Exception
                      that was raised), and the :param:`host`.
            """
            addr, port = host
            sckt = self.buildSocket(addr)
            context = self.getContext()
            connection = SSL.Connection(context, sckt)
            connection.connect(host)
            return connection

        def connectionFailed(connection, host):
            """
            Handle errors raised while attempting to create the socket, TLS/SSL
            context, and :class:`OpenSSL.SSL.Connection` object.

            @param connection: The Exception that was raised in
                               :func:`makeConnection`.
            @param host: A tuple of the host IP address as a string, and an int
                         specifying the host port, i.e. ('1.1.1.1', 443)
            """
            addr, port = host
            if isinstance(connection, IOError):
                ## On some *nix distros, /dev/random is 0600 root:root and we get
                ## a permissions error when trying to read
                if connection.message.find("[Errno 13]"):
                    raise NotRootError(
                        "%s" % connection.message.split("[Errno 13]", 1)[1])

            if isinstance(connection, socket_error):
                if connection.message.find("[Errno 101]"):
                    raise HostUnreachableError(
                        "Host unreachable: %s:%s" % (addr, port))

            log.err(connection)
            self.report['host'] = addr
            self.report['port'] = port
            self.report['state'] = 'CONNECTION_FAILED'
            return connection

        def connectionSucceeded(connection, host, timeout):
            """
            If we have created a connection, set the socket options, and log the
            connection state and peer name.

            @param connection: A :class:`OpenSSL.SSL.Connection` object.
            @param host: A tuple of the host IP and port, i.e. ('1.1.1.1', 443).
            """
            connection.setblocking(1)
            ## Set the timeout on the connection:
            ##
            ## We want to set SO_RCVTIMEO and SO_SNDTIMEO, which both are
            ## defined in the socket option definitions in <sys/socket.h>, and
            ## which both take as their value, according to socket(7), a
            ## struct timeval, which is defined in the libc manual:
            ## https://www.gnu.org/software/libc/manual/html_node/Elapsed-Time.html
            timeval = struct.pack('ll', int(timeout), 0)
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeval)
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDTIMEO, timeval)

            ## Set the connection state to client mode:
            connection.set_connect_state()

            peer_name, peer_port = connection.getpeername()
            if peer_name:
                log.msg("Connected to %s" % peer_name)
            else:
                log.debug("Couldn't get peer name from connection: %s" % host)
                log.msg("Connected to: %s" % host)
            log.msg("Connection state: %s " % connection.state_string())

            return connection

        def connectionRenegotiate(connection, host, error_message):
            log.msg("Server requested renegotiation from: %s" % host)
            log.debug("Renegotiation reason: %s" % error_message)
            log.debug("State: %s" % connection.state_string())

            if connection.renegotiate():
                log.debug("Renegotiation possible.")
                log.message("Retrying handshake with %s..." % host)
                try:
                    connection.do_handshake()
                    while connection.renegotiate_pending():
                        log.msg("Renegotiation with %s in progress..." % host)
                        log.debug("State: %s" % connection.state_string())
                        sleep(1)
                    else:
                        log.msg("Renegotiation with %s complete!" % host)
                except SSL.WantReadError, wre:
                    connection = handleWantRead(connection)
                    log.debug("State: %s" % connection.state_string())
                except SSL.WantWriteError, wwe:
                    connection = handleWantWrite(connection)
                    log.debug("State: %s" % connection.state_string())
            return connection

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

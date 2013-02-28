#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
  tls_handshake.py
  ----------------

  This file contains test cases for determining if a TLS handshake completes
  successfully, including ways to test if a TLS handshake which uses Mozilla
  Firefox's current ciphersuite list completes. Rather than using Twisted and
  OpenSSL's methods for automatically completing a handshake, which includes
  setting all the parameters, such as the ciphersuite list, these tests use
  non-blocking sockets and implement asychronous error-handling transversal of
  OpenSSL's memory BIO state machine, allowing us to determine where and why a
  handshake fails.

  This network test is a complete rewrite of a pseudonymously contributed
  script by Hackerberry Finn, in order to fit into OONI's core network tests.

  @authors: Isis Agora Lovecruft <isis@torproject.org>
  @license: see included LICENSE file
  @copyright: © 2013 Isis Lovecruft, The Tor Project Inc.
"""

from socket import error as socket_error
from time   import sleep

import os
import socket
import struct
import sys
import types

from ipaddr                 import IPAddress
from OpenSSL                import SSL
from OpenSSL.crypto         import dump_certificate, dump_privatekey
from OpenSSL.crypto         import X509Name, PKey, FILETYPE_PEM
from twisted.internet       import defer
from twisted.python         import usage
from twisted.python.failure import Failure

from ooni       import nettest, config
from ooni.utils import log, NotRootError

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
    version      = '0.0.2'

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

    @staticmethod
    def getX509Name(certificate, get_components=False):
        """
        Get the DER encoded form of the Name portions of and X509 certificate.

        @param certificate: A :class:`OpenSSL.crypto.X509Name` object.
        @param get_components: A boolean. If True, returns a list of tuples of
                               the (name, value)s of each Name field in the
                               :param:`certificate`. If False, returns the DER
                               encoded form of the Name fields of the
                               :param:`certificate`.
        """
        x509_name = None

        try:
            assert isinstance(certificate, X509Name), \
                "getX509Name takes OpenSSL.crypto.X509Name as first argument!"
            x509_name = X509Name(certificate)
        except AssertionError as ae:
            log.err(ae)
        except Exception as exc:
            log.exception(exc)

        if not x509_name is None:
            if not get_components:
                return x509_name.der()
            else:
                return x509_name.get_components()
        else:
            log.debug("getX509Name: got None for ivar x509_name")

    @staticmethod
    def getPublicKey(key):
        """
        Get the PEM-encoded format of a host certificate's public key.

        @param key: A :class:`OpenSSL.crypto.PKey` object.
        """
        try:
            assert isinstance(key, PKey), \
                "getPublicKey expects type OpenSSL.crypto.PKey for parameter key"
        except AssertionError as ae:
            log.err(ae)
        else:
            pubkey = dump_privatekey(FILETYPE_PEM, key)
            return pubkey

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

        def connectionShutdown(connection, host):
            """
            Handle shutting down a :class:`OpenSSL.SSL.Connection`, including
            correct handling of halfway shutdown connections.

            Calls to :meth:`OpenSSL.SSL.Connection.shutdown` return a boolean
            value: if the connection is already shutdown, it returns True,
            else it returns false. Thus we loop through a block which detects
            if the connection is an a partial shutdown state and corrects that
            if that is the case, else it waits for one second, then attempts
            shutting down the connection again.

            Detection of a partial shutdown state is done through
            :meth:`OpenSSL.SSL.Connection.get_shutdown` which queries OpenSSL
            for a bitvector of the server and client shutdown states. For
            example, the binary string '0b00' is an open connection, and
            '0b10' is a partially closed connection that has been shutdown on
            the serverside.

            @param connection: A :class:`OpenSSL.SSL.Connection`.

            @param host: A tuple of: a string representation of the remote
                         host's IP address, and an integer specifying the
                         port.
            """
            peername, peerport = host

            if isinstance(connection, SSL.Connection):
                log.msg("Closing connection to %s:%d..."
                        % (peername, peerport))
                while not connection.shutdown():
                    ## if the connection is halfway shutdown, we have to
                    ## wait for a ZeroReturnError on connection.recv():
                    if (bin(connection.get_shutdown()) == '0b01') \
                            or (bin(connection.get_shutdown()) == '0b10'):
                        try:
                            _read_buffer = connection.pending()
                            connection.recv(_read_buffer)
                        except SSL.ZeroReturnError, zre: continue
                    else:
                        sleep(1)
                else:
                    log.msg("Closed connection to %s:%d"
                            % (peername, peerport))
            elif isinstance(connection, types.NoneType):
                log.debug("connectionShutdown: got NoneType for connection")
            else:
                log.debug("connectionShutdown: expected connection, got %s"
                          % connection.__repr__())
            return connection

        def handleWantRead(connection):
            """
            From OpenSSL memory BIO documentation on ssl_read():

                If the underlying BIO is blocking, SSL_read() will only
                return, once the read operation has been finished or an error
                occurred, except when a renegotiation take place, in which
                case a SSL_ERROR_WANT_READ may occur. This behaviour can be
                controlled with the SSL_MODE_AUTO_RETRY flag of the
                SSL_CTX_set_mode(3) call.

                If the underlying BIO is non-blocking, SSL_read() will also
                return when the underlying BIO could not satisfy the needs of
                SSL_read() to continue the operation. In this case a call to
                SSL_get_error(3) with the return value of SSL_read() will
                yield SSL_ERROR_WANT_READ or SSL_ERROR_WANT_WRITE. As at any
                time a re-negotiation is possible, a call to SSL_read() can
                also cause write operations!  The calling process then must
                repeat the call after taking appropriate action to satisfy the
                needs of SSL_read(). The action depends on the underlying
                BIO. When using a non-blocking socket, nothing is to be done,
                but select() can be used to check for the required condition.

            And from the OpenSSL memory BIO documentation on ssl_get_error():

                SSL_ERROR_WANT_READ, SSL_ERROR_WANT_WRITE

                The operation did not complete; the same TLS/SSL I/O function
                should be called again later. If, by then, the underlying BIO
                has data available for reading (if the result code is
                SSL_ERROR_WANT_READ) or allows writing data
                (SSL_ERROR_WANT_WRITE), then some TLS/SSL protocol progress
                will take place, i.e. at least part of an TLS/SSL record will
                be read or written. Note that the retry may again lead to a
                SSL_ERROR_WANT_READ or SSL_ERROR_WANT_WRITE condition. There
                is no fixed upper limit for the number of iterations that may
                be necessary until progress becomes visible at application
                protocol level.

                For socket BIOs (e.g. when SSL_set_fd() was used), select() or
                poll() on the underlying socket can be used to find out when
                the TLS/SSL I/O function should be retried.

                Caveat: Any TLS/SSL I/O function can lead to either of
                SSL_ERROR_WANT_READ and SSL_ERROR_WANT_WRITE. In particular,
                SSL_read() or SSL_peek() may want to write data and
                SSL_write() may want to read data. This is mainly because
                TLS/SSL handshakes may occur at any time during the protocol
                (initiated by either the client or the server); SSL_read(),
                SSL_peek(), and SSL_write() will handle any pending
                handshakes.

            Also, see http://stackoverflow.com/q/3952104
            """
            try:
                while connection.want_read():
                    log.debug("Connection to %s HAS want_read" % host)
                    _read_buffer = connection.pending()
                    log.debug("Rereading %d bytes..." % _read_buffer)
                    sleep(1)
                    rereceived = connection.recv(int(_read_buffer))
                    log.debug("Received %d bytes" % rereceived)
                    log.debug("State: %s" % connection.state_string())
                else:
                    peername, peerport = connection.getpeername()
                    log.debug("Connection to %s:%s DOES NOT HAVE want_read"
                              % (peername, peerport))
                    log.debug("State: %s" % connection.state_string())
            except SSL.WantWriteError, wwe:
                log.debug("Got WantWriteError while handling want_read")
                log.debug("WantWriteError: %s" % wwe.message)
                log.debug("Switching to handleWantWrite()...")
                handleWantWrite(connection)
            return connection

        def handleWantWrite(connection):
            """
            See :func:`handleWantRead`.
            """
            try:
                while connection.want_write():
                    log.debug("Connection to %s HAS want_write" % host)
                    sleep(1)
                    resent = connection.send("o\r\n")
                    log.debug("Sent: %d" % resent)
                    log.debug("State: %s" % connection.state_string())
            except SSL.WantReadError, wre:
                log.debug("Got WantReadError while handling want_write")
                log.debug("WantReadError: %s" % wre.message)
                log.debug("Switching to handleWantRead()...")
                handleWantRead(connection)
            return connection

        def doHandshake(connection):
            """
            Attemp a TLS/SSL handshake with the host.

            If, after the first attempt at handshaking, OpenSSL's memory BIO
            state machine does not report success, then try reading and
            writing from the connection, and handle any SSL_ERROR_WANT_READ or
            SSL_ERROR_WANT_WRITE which occurs.

            If multiple want_reads occur, then try renegotiation with the
            host, and start over. If multiple want_writes occur, then it is
            possible that the connection has timed out, and move on to the
            connectionShutdown step.

            @param connection: A :class:`OpenSSL.SSL.Connection`.
            @ivar peername: The host IP address, as reported by getpeername().
            @ivar peerport: The host port, reported by getpeername().
            @ivar sent: The number of bytes sent to to the remote host.
            @ivar received: The number of bytes received from the remote host.
            @ivar _read_buffer: An integer for the max bytes that can be read
                                from the connection.
            @returns: The :param:connection with handshake completed, else
                      the unhandled error that was raised.
            """
            peername, peerport = connection.getpeername()

            log.msg("Attempting handshake: %s" % peername)
            connection.do_handshake()
            log.debug("State: %s" % connection.state_string())
            if connection.state_string() == \
                    'SSL negotiation finished successfully':
                ## jump to handshakeSuccessful and get certchain
                return connection

            else:
                sent = connection.send("o\r\n")
                log.debug("State: %s" % connection.state_string())
                log.debug("Transmitted %d bytes" % sent)

                _read_buffer = connection.pending()
                log.debug("Max bytes in receive buffer: %d" % _read_buffer)

                try:
                    received = connection.recv(int(_read_buffer))
                except SSL.WantReadError, wre:
                    if connection.want_read():
                        connection = handleWantRead(connection)
                    else:
                        ## if we still have an SSL_ERROR_WANT_READ, then try
                        ## to renegotiate
                        connection = connectionRenegotiate(connection,
                                                           connection.getpeername(),
                                                           wre.message)
                except SSL.WantWriteError, wwe:
                    log.debug("State: %s" % connection.state_string())
                    if connection.want_write():
                        connection = handleWantWrite(connection)
                    else:
                        log.msg("Connection to %s:%s timed out."
                                % (peername, str(peerport)))
                else:
                    log.msg("Received: %s" % received)
                    log.debug("State: %s" % connection.state_string())

            return connection

        def handshakeSucceeded(connection):
            """
            Get the details from the server certificate, cert chain, and
            server ciphersuite list, and put them in our report.

            WARNING: do *not* do this:
                >>> server_cert.get_pubkey()
                    <OpenSSL.crypto.PKey at 0x4985d28>
                >>> pk = server_cert.get_pubkey()
                >>> pk.check
                    <function check>
                >>> pk.check()
                    Segmentation fault

            @param connection: A :class:`OpenSSL.SSL.Connection`.
            @returns: None.
            """
            host, port = connection.getpeername()
            server_cert = self.getPeerCert(connection)
            server_cert_chain = self.getPeerCert(connection, get_chain=True)

            s_cert          = connection.get_peer_certificate()
            cert_subject    = self.getX509Name(s_cert.get_subject(),
                                               get_components=True)
            cert_subj_hash  = s_cert.subject_name_hash()
            cert_issuer     = self.getX509Name(s_cert.get_issuer(),
                                               get_components=True)
            cert_public_key = self.getPublicKey(s_cert.get_pubkey())
            cert_serial_no  = s_cert.get_serial_number()
            cert_sig_algo   = s_cert.get_signature_algorithm()

            self.report['host'] = host
            self.report['port'] = port
            self.report['state'] = connection.state_string()
            self.report['renegotiations'] = connection.total_renegotiations()
            self.report['server_cert'] = server_cert
            self.report['server_cert_chain'] = \
                ''.join([cert for cert in server_cert_chain])
            self.report['server_ciphersuite'] = connection.get_cipher_list()
            self.report['cert_subject'] = str(cert_subject)
            self.report['cert_subj_hash'] = str(cert_subj_hash)
            self.report['cert_issuer'] = str(cert_issuer)
            ## xxx this needs to be parsed into PEM also
            self.report['cert_public_key'] = str(cert_public_key)
            self.report['cert_serial_no'] = str(cert_serial_no)
            self.report['cert_sig_algo'] = str(cert_sig_algo)

            ## The session's master key is only valid for that session, and
            ## will allow us to decrypt any packet captures (if they were
            ## collected). Because we are not requesting URLs, only host:port
            ## (which would be visible in pcaps anyway, since the FQDN is
            ## never encrypted) I do not see a way for this to log any user or
            ## identifying information. Correct me if I'm wrong.
            self.report['session_key'] = connection.master_key()

            ## xxx do we need this?
            #return connection

        def handshakeFailed(connection, host):
            """
            xxx fill me in

            @param connection: A :class:`twisted.python.failure.Failure` or
                               :class:`exceptions.Exception`.
            @param host: A tuple of the host IP and port, i.e. ('1.1.1.1', 443).
            @returns: None.
            """
            addr, port = host
            log.msg("Handshake with %s:%d failed!" % host)
            self.report['host'] = host
            self.report['port'] = port
            self.report['state'] = "HANDSHAKE_FAILED"
            ## xxx do we need this?
            #return connection

        @defer.inlineCallbacks
        def deferMakeConnection(host):
            connection = yield makeConnection(host)
            if isinstance(connection, Failure) \
                    or isinstance(connection, Exception):
                failed = connectionFailed(connection, host)
                defer.returnValue(failed)
            else:
                defer.returnValue(connection)

        connection = deferMakeConnection(self.input)
        connection.addCallbacks(connectionSucceeded, connectionFailed,
                                callbackArgs=[self.input, self.timeout],
                                errbackArgs=[self.input])

        handshake = defer.Deferred()
        handshake.addCallback(doHandshake)
        handshake.addCallbacks(handshakeSucceeded, handshakeFailed,
                               errbackArgs=[self.input])

        connection.chainDeferred(handshake)
        connection.addCallbacks(connectionShutdown, defer.passthru,
                                callbackArgs=[self.input])
        connection.addBoth(log.exception)

        return connection

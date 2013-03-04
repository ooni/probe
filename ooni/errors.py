from twisted.internet.defer import TimeoutError as DeferTimeoutError
from twisted.web._newclient import ResponseNeverReceived

from twisted.internet.error import ConnectionRefusedError, TCPTimedOutError
from twisted.internet.error import DNSLookupError
from twisted.internet.error import TimeoutError as GenericTimeoutError

from txsocksx.errors import SOCKSError
from txsocksx.errors import MethodsNotAcceptedError, AddressNotSupported
from txsocksx.errors import ConnectionError, NetworkUnreachable
from txsocksx.errors import ConnectionLostEarly, ConnectionNotAllowed
from txsocksx.errors import NoAcceptableMethods, ServerFailure
from txsocksx.errors import HostUnreachable, ConnectionRefused
from txsocksx.errors import TTLExpired, CommandNotSupported

from socket import gaierror
from ooni.utils import log
def handleAllFailures(failure):
    """
    Here we make sure to trap all the failures that are supported by the
    failureToString function and we return the the string that represents the
    failure.
    """
    failure.trap(ConnectionRefusedError, gaierror, DNSLookupError,
            TCPTimedOutError, ResponseNeverReceived, DeferTimeoutError,
            GenericTimeoutError,
            SOCKSError, MethodsNotAcceptedError, AddressNotSupported,
            ConnectionError, NetworkUnreachable, ConnectionLostEarly,
            ConnectionNotAllowed, NoAcceptableMethods, ServerFailure,
            HostUnreachable, ConnectionRefused, TTLExpired, CommandNotSupported)

    return failureToString(failure)

def failureToString(failure):
    """
    Given a failure instance return a string representing the kind of error
    that occurred.

    Args:

        failure: a :class:twisted.internet.error instance

    Returns:

        A string representing the HTTP response error message.
    """
    string = None
    if isinstance(failure.value, ConnectionRefusedError):
        log.err("Connection refused. The backend may be down")
        string = 'connection_refused_error'

    elif isinstance(failure.value, gaierror):
        log.err("Address family for hostname not supported")
        string = 'address_family_not_supported_error'

    elif isinstance(failure.value, DNSLookupError):
        log.err("DNS lookup failure")
        string = 'dns_lookup_error'

    elif isinstance(failure.value, TCPTimedOutError):
        log.err("TCP Timed Out Error")
        string = 'tcp_timed_out_error'

    elif isinstance(failure.value, ResponseNeverReceived):
        log.err("Response Never Received")
        string = 'response_never_received'

    elif isinstance(failure.value, DeferTimeoutError):
        log.err("Deferred Timeout Error")
        string = 'deferred_timeout_error'

    elif isinstance(failure.value, GenericTimeoutError):
        log.err("Time Out Error")
        string = 'generic_timeout_error'

    elif isinstance(failure.value, ServerFailure):
        log.err("SOCKS error: ServerFailure")
        string = 'socks_server_failure'

    elif isinstance(failure.value, ConnectionNotAllowed):
        log.err("SOCKS error: ConnectionNotAllowed")
        string = 'socks_connection_not_allowed'

    elif isinstance(failure.value, NetworkUnreachable):
        log.err("SOCKS error: NetworkUnreachable")
        string = 'socks_network_unreachable'

    elif isinstance(failure.value, HostUnreachable):
        log.err("SOCKS error: HostUnreachable")
        string = 'socks_host_unreachable'

    elif isinstance(failure.value, ConnectionRefused):
        log.err("SOCKS error: ConnectionRefused")
        string = 'socks_connection_refused'

    elif isinstance(failure.value, TTLExpired):
        log.err("SOCKS error: TTLExpired")
        string = 'socks_ttl_expired'

    elif isinstance(failure.value, CommandNotSupported):
        log.err("SOCKS error: CommandNotSupported")
        string = 'socks_command_not_supported'

    elif isinstance(failure.value, AddressNotSupported):
        log.err("SOCKS error: AddressNotSupported")
        string = 'socks_address_not_supported'
    elif isinstance(failure.value, SOCKSError):
        log.err("Generic SOCKS error")
        string = 'socks_error'

    else:
        log.err("Unknown failure type: %s" % type(failure))
        string = 'unknown_failure %s' % str(failure.value)

    return string

class DirectorException(Exception):
    pass

class UnableToStartTor(DirectorException):
    pass

class InvalidOONIBCollectorAddress(Exception):
    pass

class AllReportersFailed(Exception):
    pass

class ReportNotCreated(Exception):
    pass

class ReportAlreadyClosed(Exception):
    pass


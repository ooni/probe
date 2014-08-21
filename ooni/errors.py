from twisted.internet.defer import CancelledError
from twisted.internet.defer import TimeoutError as DeferTimeoutError
from twisted.web._newclient import ResponseNeverReceived
from twisted.web.error import Error

from twisted.internet.error import ConnectionRefusedError, TCPTimedOutError
from twisted.internet.error import DNSLookupError, ConnectError, ConnectionLost
from twisted.internet.error import TimeoutError as GenericTimeoutError

from twisted.python import usage

from txsocksx.errors import SOCKSError
from txsocksx.errors import MethodsNotAcceptedError, AddressNotSupported
from txsocksx.errors import ConnectionError, NetworkUnreachable
from txsocksx.errors import ConnectionLostEarly, ConnectionNotAllowed
from txsocksx.errors import NoAcceptableMethods, ServerFailure
from txsocksx.errors import HostUnreachable, ConnectionRefused
from txsocksx.errors import TTLExpired, CommandNotSupported

from socket import gaierror


def handleAllFailures(failure):
    """
    Here we make sure to trap all the failures that are supported by the
    failureToString function and we return the the string that represents the
    failure.
    """
    failure.trap(
        ConnectionRefusedError,
        gaierror,
        DNSLookupError,
        TCPTimedOutError,
        ResponseNeverReceived,
        DeferTimeoutError,
        GenericTimeoutError,
        SOCKSError,
        MethodsNotAcceptedError,
        AddressNotSupported,
        ConnectionError,
        NetworkUnreachable,
        ConnectionLostEarly,
        ConnectionNotAllowed,
        NoAcceptableMethods,
        ServerFailure,
        HostUnreachable,
        ConnectionRefused,
        TTLExpired,
        CommandNotSupported,
        ConnectError,
        ConnectionLost,
        CancelledError)

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
        # log.err("Connection refused.")
        string = 'connection_refused_error'

    elif isinstance(failure.value, ConnectionLost):
        # log.err("Connection lost.")
        string = 'connection_lost_error'

    elif isinstance(failure.value, ConnectError):
        # log.err("Connect error.")
        string = 'connect_error'

    elif isinstance(failure.value, gaierror):
        # log.err("Address family for hostname not supported")
        string = 'address_family_not_supported_error'

    elif isinstance(failure.value, DNSLookupError):
        # log.err("DNS lookup failure")
        string = 'dns_lookup_error'

    elif isinstance(failure.value, TCPTimedOutError):
        # log.err("TCP Timed Out Error")
        string = 'tcp_timed_out_error'

    elif isinstance(failure.value, ResponseNeverReceived):
        # log.err("Response Never Received")
        string = 'response_never_received'

    elif isinstance(failure.value, DeferTimeoutError):
        # log.err("Deferred Timeout Error")
        string = 'deferred_timeout_error'

    elif isinstance(failure.value, GenericTimeoutError):
        # log.err("Time Out Error")
        string = 'generic_timeout_error'

    elif isinstance(failure.value, ServerFailure):
        # log.err("SOCKS error: ServerFailure")
        string = 'socks_server_failure'

    elif isinstance(failure.value, ConnectionNotAllowed):
        # log.err("SOCKS error: ConnectionNotAllowed")
        string = 'socks_connection_not_allowed'

    elif isinstance(failure.value, NetworkUnreachable):
        # log.err("SOCKS error: NetworkUnreachable")
        string = 'socks_network_unreachable'

    elif isinstance(failure.value, HostUnreachable):
        # log.err("SOCKS error: HostUnreachable")
        string = 'socks_host_unreachable'

    elif isinstance(failure.value, ConnectionRefused):
        # log.err("SOCKS error: ConnectionRefused")
        string = 'socks_connection_refused'

    elif isinstance(failure.value, TTLExpired):
        # log.err("SOCKS error: TTLExpired")
        string = 'socks_ttl_expired'

    elif isinstance(failure.value, CommandNotSupported):
        # log.err("SOCKS error: CommandNotSupported")
        string = 'socks_command_not_supported'

    elif isinstance(failure.value, AddressNotSupported):
        # log.err("SOCKS error: AddressNotSupported")
        string = 'socks_address_not_supported'

    elif isinstance(failure.value, SOCKSError):
        # log.err("Generic SOCKS error")
        string = 'socks_error'

    elif isinstance(failure.value, CancelledError):
        # log.err("Task timed out")
        string = 'task_timed_out'

    else:
        # log.err("Unknown failure type: %s" % type(failure.value))
        string = 'unknown_failure %s' % str(failure.value)

    return string


class DirectorException(Exception):
    pass


class UnableToStartTor(DirectorException):
    pass


class InvalidOONIBCollectorAddress(Exception):
    pass


class InvalidOONIBBouncerAddress(Exception):
    pass


class AllReportersFailed(Exception):
    pass


class GeoIPDataFilesNotFound(Exception):
    pass


class ReportNotCreated(Exception):
    pass


class ReportAlreadyClosed(Exception):
    pass


class TorStateNotFound(Exception):
    pass


class TorControlPortNotFound(Exception):
    pass


class InsufficientPrivileges(Exception):
    pass


class ProbeIPUnknown(Exception):
    pass


class NoMoreReporters(Exception):
    pass


class TorNotRunning(Exception):
    pass


class OONIBError(Exception):
    pass


class OONIBInvalidRequest(OONIBError):
    pass


class OONIBReportError(OONIBError):
    pass


class OONIBReportUpdateError(OONIBReportError):
    pass


class OONIBReportCreationError(OONIBReportError):
    pass


class OONIBTestDetailsLookupError(OONIBReportError):
    pass


class OONIBInputError(OONIBError):
    pass


class OONIBInputDescriptorNotFound(OONIBInputError):
    pass


class UnableToLoadDeckInput(Exception):
    pass


class CouldNotFindTestHelper(Exception):
    pass


class CouldNotFindTestCollector(Exception):
    pass


class NetTestNotFound(Exception):
    pass


class MissingRequiredOption(Exception):
    def __init__(self, message, net_test_loader):
        super(MissingRequiredOption, self).__init__()
        self.net_test_loader = net_test_loader
        self.message = message

    def __str__(self):
        return ','.join(self.message)


class OONIUsageError(usage.UsageError):
    def __init__(self, net_test_loader):
        super(OONIUsageError, self).__init__()
        self.net_test_loader = net_test_loader


class FailureToLoadNetTest(Exception):
    pass


class NoPostProcessor(Exception):
    pass


class InvalidOption(Exception):
    pass


class IncoherentOptions(Exception):
    def __init__(self, first_options, second_options):
        super(IncoherentOptions, self).__init__()
        self.message = "%s is different to %s" % (first_options, second_options)

    def __str__(self):
        return self.message


class TaskTimedOut(Exception):
    pass


class InvalidInputFile(Exception):
    pass


class ReporterException(Exception):
    pass


class InvalidDestination(ReporterException):
    pass


class ReportLogExists(Exception):
    pass


class InvalidConfigFile(Exception):
    pass


class ConfigFileIncoherent(Exception):
    pass


def get_error(error_key):
    if error_key == 'test-helpers-key-missing':
        return CouldNotFindTestHelper
    if error_key == 'input-descriptor-not-found':
        return OONIBInputDescriptorNotFound
    if error_key == 'invalid-request':
        return OONIBInvalidRequest
    elif isinstance(error_key, int):
        return Error("%d" % error_key)
    else:
        return OONIBError

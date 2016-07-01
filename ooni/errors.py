from twisted.internet.defer import CancelledError
from twisted.internet.defer import TimeoutError as DeferTimeoutError
from twisted.web._newclient import ResponseNeverReceived
from twisted.web.error import Error

from twisted.internet.error import ConnectionRefusedError, TCPTimedOutError
from twisted.internet.error import DNSLookupError, ConnectError, ConnectionLost
from twisted.names.error import DNSNameError, DNSServerError
from twisted.internet.error import TimeoutError as GenericTimeoutError
from twisted.internet.error import ProcessDone, ConnectionDone

from twisted.python import usage

from txsocksx.errors import SOCKSError
from txsocksx.errors import MethodsNotAcceptedError, AddressNotSupported
from txsocksx.errors import ConnectionError, NetworkUnreachable
from txsocksx.errors import ConnectionLostEarly, ConnectionNotAllowed
from txsocksx.errors import NoAcceptableMethods, ServerFailure
from txsocksx.errors import HostUnreachable, ConnectionRefused
from txsocksx.errors import TTLExpired, CommandNotSupported

from socket import gaierror

known_failures = [
    (ConnectionRefusedError, 'connection_refused_error'),
    (ConnectionLost, 'connection_lost_error'),
    (CancelledError, 'task_timed_out'),
    (gaierror, 'address_family_not_supported_error'),
    (DNSLookupError, 'dns_lookup_error'),
    (DNSNameError, 'dns_name_error'),
    (DNSServerError, 'dns_server_failure'),
    (TCPTimedOutError, 'tcp_timed_out_error'),
    (ResponseNeverReceived, 'response_never_received'),
    (DeferTimeoutError, 'deferred_timeout_error'),
    (GenericTimeoutError, 'generic_timeout_error'),
    (MethodsNotAcceptedError, 'socks_methods_not_supported'),
    (AddressNotSupported, 'socks_address_not_supported'),
    (NetworkUnreachable, 'socks_network_unreachable'),
    (ConnectionError, 'socks_connect_error'),
    (ConnectionLostEarly, 'socks_connection_lost_early'),
    (ConnectionNotAllowed, 'socks_connection_not_allowed'),
    (NoAcceptableMethods, 'socks_no_acceptable_methods'),
    (ServerFailure, 'socks_server_failure'),
    (HostUnreachable, 'socks_host_unreachable'),
    (ConnectionRefused, 'socks_connection_refused'),
    (TTLExpired, 'socks_ttl_expired'),
    (CommandNotSupported, 'socks_command_not_supported'),
    (SOCKSError, 'socks_error'),
    (ProcessDone, 'process_done'),
    (ConnectionDone, 'connection_done'),
    (ConnectError, 'connect_error'),
]

def handleAllFailures(failure):
    """
    Trap all the known Failures and we return a string that
    represents the failure. Any unknown Failures will be reraised and
    returned by failure.trap().
    """

    failure.trap(*[failure_type for failure_type, _ in known_failures])
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

    for failure_type, failure_string in known_failures:
        if isinstance(failure.value, failure_type):
            return failure_string
    # Failure without a corresponding failure message
    return 'unknown_failure %s' % str(failure.value)

class DirectorException(Exception):
    pass


class UnableToStartTor(DirectorException):
    pass


class InvalidAddress(Exception):
    pass

class InvalidOONIBCollectorAddress(InvalidAddress):
    pass


class InvalidOONIBBouncerAddress(InvalidAddress):
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


class OONIBInvalidInputHash(OONIBError):
    pass


class OONIBInvalidNettestName(OONIBError):
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

class MissingTestHelper(MissingRequiredOption):
    pass

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
    elif error_key == 'input-descriptor-not-found':
        return OONIBInputDescriptorNotFound
    elif error_key == 'invalid-request':
        return OONIBInvalidRequest
    elif error_key == 'invalid-input-hash':
        return OONIBInvalidInputHash
    elif error_key == 'invalid-nettest-name':
        return OONIBInvalidNettestName
    elif isinstance(error_key, int):
        return Error("%d" % error_key)
    else:
        return OONIBError


class IfaceError(Exception):
    pass


class ProtocolNotRegistered(Exception):
    pass


class ProtocolAlreadyRegistered(Exception):
    pass


class LibraryNotInstalledError(Exception):
    pass


class InsecureBackend(Exception):
    pass

class CollectorUnsupported(Exception):
    pass

class HTTPSCollectorUnsupported(CollectorUnsupported):
    pass


class BackendNotSupported(Exception):
    pass


class NoReachableCollectors(Exception):
    pass


class NoReachableTestHelpers(Exception):
    pass


class InvalidPreferredBackend(Exception):
    pass

class ValueChecker(object):
    """
    A class for general purpose value checks on commandline parameters
    passed to subclasses of :class:`twisted.python.usage.Options`.
    """
    def __init__(self, coerce_doc=None):
        self.coerce_doc = coerce_doc

    def port_check(self, port, range_min=1024, range_max=65535):
        """
        Check that given ports are in the allowed range for an unprivileged
        user.

        :param port:
            The port to check.
        :param range_min:
            The minimum allowable port number.
        :param range_max:
            The minimum allowable port number.
        :param coerce_doc:
            The documentation string to show in the optParameters menu, see
            :class:`twisted.python.usage.Options`.
        """
        if self.coerce_doc is not None:
            coerceDoc = self.coerce_doc

        assert type(port) is int
        if port not in range(range_min, range_max):
            raise ValueError("Port out of range")
            log.err()

    @staticmethod
    def uid_check(error_message):
        """
        Check that we're not root. If we are, setuid(1000) to normal user if
        we're running on a posix-based system, and if we're on Windows just
        tell the user that we can't be run as root with the specified options
        and then exit.

        :param error_message:
            The string to log as an error message when the uid check fails.
        """
        uid, gid = os.getuid(), os.getgid()
        if uid == 0 and gid == 0:
            log.msg(error_message)
        if os.name == 'posix':
            log.msg("Dropping privileges to normal user...")
            os.setgid(1000)
            os.setuid(1000)
        else:
            sys.exit(0)

    @staticmethod
    def dir_check(d):
        """Check that the given directory exists."""
        if not os.path.isdir(d):
            raise ValueError("%s doesn't exist, or has wrong permissions"
                             % d)

    @staticmethod
    def file_check(f):
        """Check that the given file exists."""
        if not os.path.isfile(f):
            raise ValueError("%s does not exist, or has wrong permissions"
                             % f)


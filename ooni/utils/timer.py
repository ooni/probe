#
# timer.py
# ----------
# OONI utilities for adding timeouts to functions and to Deferreds.
#
# :author: Isis Lovecruft
# :version: 0.1.0-pre-alpha
# :license: see include LICENSE file
# :copyright: copyright (c) 2012, Isis Lovecruft, The Tor Project Inc.
# 

class TimeoutError(Exception):
    """Raised when a timer runs out."""
    pass

def timeout(seconds, e=None):
    """
    A decorator for blocking methods to cause them to timeout. Can be used
    like this: 
        @timeout(30)
        def foo():
            for x in xrange(1000000000):
                print x
    or like this:
        ridiculous = timeout(30)(foo)

    :param seconds:
        Number of seconds to wait before raising :class:`TimeoutError`.
    :param e:
        Error message to pass to :class:`TimeoutError`. Default None.
    """
    from signal    import alarm, signal, SIGALRM
    from functools import wraps

    def decorator(func):
        def _timeout(signum, frame):
            raise TimeoutError, e
        def wrapper(*args, **kwargs):
            signal(SIGALRM, _timeout)
            alarm(seconds)
            try:
                res = func(*args, **kwargs)
            finally:
                alarm(0)
            return res
        return wraps(func)(wrapper)
    return decorator

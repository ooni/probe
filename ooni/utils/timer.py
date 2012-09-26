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

def timeout(secs, e=None):
    """
    A decorator for blocking methods to cause them to timeout.
    """
    import signal
    import functools.wraps
    def decorator(func):
        def _timeout(signum, frame):
            raise TimeoutError, e

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _timeout)
            signal.alarm(secs)
            try:
                res = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return res
        return functools.wraps(func)(wrapper)
    return decorator

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
        def foo(arg1, kwarg="baz"):
            for x in xrange(1000000000):
                print "%s %s" % (arg1, kwarg)
                print x

    or like this:

        ridiculous = timeout(30)(foo("bar"))

    :param seconds:
        Number of seconds to wait before raising :class:`TimeoutError`.
    :param e:
        Error message to pass to :class:`TimeoutError`. Default None.
    :return:
        The result of the original function, or else an instance of 
        :class:`TimeoutError`.
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

def deferred_timeout(seconds, e=None):
    """
    Decorator for adding a timeout to an instance of a
    :class:`twisted.internet.defer.Deferred`. Can be used like this:

        @deferred_timeout(30)
        def foo(arg1, kwarg="baz"):
            for x in xrange(1000000000):
                print "%s %s" % (arg1, kwarg)
                print x

    or like this:

        ridiculous = deferred_timeout(30)(foo("bar"))

    :param seconds:
        Number of seconds to wait before raising :class:`TimeoutError`.
    :param e:
        Error message to pass to :class:`TimeoutError`. Default None.
    :return:
        The result of the orginal :class:`twisted.internet.defer.Deferred`
        or else a :class:`TimeoutError`.
    """
    from twisted.internet import defer, reactor

    def wrapper(func):
        @defer.inlineCallbacks
        def _timeout(*args, **kwargs):
            d_original = func(*args, **kwargs)
            if not isinstance(d_original, defer.Deferred):
                defer.returnValue(d_original) ## fail gracefully
            d_timeout = defer.Deferred()
            timeup = reactor.callLater(seconds, d_timeout.callback, None)
            try:
                original_result, timeout_result = \
                    yield defer.DeferredList([d_original, d_timeout],
                                             fireOnOneCallback=True,
                                             fireOnOneErrback=True,
                                             consumeErrors=True)
            except defer.FirstError, dfe:
                assert dfe.index == 0         ## error in original
                timeup.cancel()
                dfe.subFailure.raiseException()
            else:
                if d_timeout.called:          ## timeout
                    d_original.cancel()
                    raise TimeoutError, e
            timeup.cancel()                   ## no timeout
            defer.returnValue(d_original)
        return _timeout
    return wrapper


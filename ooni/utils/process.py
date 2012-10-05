#
# process.py
# ----------
# OONI utilities for dealing with starting and stopping processes.
#
# :author: Isis Lovecruft
# :version: 0.1.0-pre-alpha
# :license: see include LICENSE file
# :copyright: copyright (c) 2012, Isis Lovecruft, The Tor Project Inc.
# 

from twisted.internet import defer

@defer.inlineCallbacks
def singleton_semaphore(deferred_process_init, 
                        callbacks=[], errbacks=[],
                        max_inits=1):
    """
    Initialize a process only once, and do not return until
    that initialization is complete. If the keyword parameter max_inits=
    is given, run the process a maximum of that number of times.

    :param deferred_process_init:
        A deferred which returns a connected process via
        :meth:`twisted.internet.reactor.spawnProcess`.
    :param callbacks:
        A list of callback functions to add to the initialized processes'
        deferred.
    :param errbacks:
        A list of errback functions to add to the initialized processes'
        deferred.
    :param max_inits:
        An integer specifying the maximum number of allowed
        initializations for :param:deferred_process_init. If no maximum
        is given, only one instance (a singleton) of the process is
        initialized.
    :return:
        The final state of the :param deferred_process_init: after the
        callback chain has completed. This should be a fully initialized
        process connected to a :class:`twisted.internet.reactor`.
    """
    assert type(callbacks) is list
    assert type(errbacks) is list
    assert type(max_inits) is int

    for cb in callbacks:
        deferred_process_init.addCallback(cb)
    for eb in errbacks:
        deferred_process_init.addErrback(eb)

    only_this_many = defer.DeferredSemaphore(max_inits)
    singleton = yield only_this_many.run(deferred_process_init)
    defer.returnValue(singleton)


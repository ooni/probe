# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

from functools import wraps
import sys
import os
import traceback
import logging

from twisted.python import log as txlog
from twisted.python import util
from twisted.python.failure import Failure
from twisted.python.logfile import DailyLogFile

from ooni import otime
from ooni import config


class LogWithNoPrefix(txlog.FileLogObserver):
    def emit(self, eventDict):
        text = txlog.textFromEventDict(eventDict)
        if text is None:
            return

        util.untilConcludes(self.write, "%s\n" % text)
        util.untilConcludes(self.flush)  # Hoorj!

def start(logfile=None, application_name="ooniprobe"):
    daily_logfile = None

    if not logfile:
        logfile = config.basic.logfile

    log_folder = os.path.dirname(logfile)
    log_filename = os.path.basename(logfile)

    daily_logfile = DailyLogFile(log_filename, log_folder)

    txlog.msg("Starting %s on %s (%s UTC)" %  (application_name, otime.prettyDateNow(),
                                                 otime.utcPrettyDateNow()))

    txlog.startLoggingWithObserver(LogWithNoPrefix(sys.stdout).emit)
    txlog.addObserver(txlog.FileLogObserver(daily_logfile).emit)

def stop():
    print "Stopping OONI"

def msg(msg, *arg, **kw):
    print "%s" % msg

def debug(message, *arg, **kw):
    if config.advanced.debug:
        print "[D] %s" % message

def warn(message, *arg, **kw):
    if config.advanced.show_warnings:
        print "[W] %s" % message

def err(message, *arg, **kw):
    print "[!] %s" % message

def exception(error):
    """
    Error can either be an error message to print to stdout and to the logfile
    or it can be a twisted.python.failure.Failure instance.
    """
    if isinstance(error, Failure):
        error.printTraceback()
    else:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)

def fail(*failure):
    logging.critical(failure)

def catch(func):
    """
    Quick wrapper to add around test methods for debugging purposes,
    catches the given Exception. Use like so:

        @log.catcher
        def foo(bar):
            if bar == 'baz':
                raise Exception("catch me no matter what I am")
        foo("baz")
    """
    def _catch(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception, exc:
            exception(exc)
    return _catch

class LoggerFactory(object):
    """
    This is a logger factory to be used by oonib
    """
    def __init__(self, options):
        pass

    def start(self, application):
        # XXX parametrize this
        start('oonib.log', "OONIB")

    def stop(self):
        txlog.msg("Stopping OONIB")


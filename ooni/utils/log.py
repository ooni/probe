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
from twisted.python.logfile import DailyLogFile

from ooni.utils import otime
from ooni import config

def start(logfile=None, application_name="ooniprobe"):
    daily_logfile = None

    if not logfile:
        logfile = config.basic.logfile

    log_folder = os.path.dirname(logfile)
    log_filename = os.path.basename(logfile)

    daily_logfile = DailyLogFile(log_filename, log_folder)

    txlog.msg("Starting %s on %s (%s UTC)" %  (application_name, otime.prettyDateNow(),
                                                 otime.utcPrettyDateNow()))
    logging.basicConfig()
    python_logging = txlog.PythonLoggingObserver(application_name)

    if config.advanced.debug:
        python_logging.logger.setLevel(logging.DEBUG)
    else:
        python_logging.logger.setLevel(logging.INFO)

    txlog.startLoggingWithObserver(python_logging.emit)

    txlog.addObserver(txlog.FileLogObserver(daily_logfile).emit)

def stop():
    txlog.msg("Stopping OONI")

def msg(msg, *arg, **kw):
    txlog.msg(msg, logLevel=logging.INFO, *arg, **kw)

def debug(msg, *arg, **kw):
    txlog.msg(msg, logLevel=logging.DEBUG, *arg, **kw)

def warn(msg, *arg, **kw):
    txlog.logging.captureWarnings('true')
    txlog.logging.warn(msg)
    #txlog.showwarning()

def err(msg, *arg, **kw):
    txlog.err("Error: " + str(msg), logLevel=logging.ERROR, *arg, **kw)

def exception(msg):
    txlog.err(msg)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback)

def exception(*msg):
    logging.exception(msg)

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
        start('/tmp/oonib.log', "OONIB")

    def stop(self):
        txlog.msg("Stopping OONIB")


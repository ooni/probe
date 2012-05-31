"""
OONI logging facility.
"""
import sys
import logging
import warnings

from twisted.python import log

# Logging levels
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

def _get_log_level(level):
    if not level:
        return INFO
    else:
        return level

def start(logfile=None, loglevel=None, logstdout=True):
    if log.defaultObserver:
        loglevel = _get_log_level(loglevel)
        logfile = logfile
        file = open(logfile, 'a') if logfile else sys.stderr
        log.startLogging(file, setStdout=logstdout)
        msg("Started OONI")

def msg(message, level=INFO, **kw):
    log.msg(message, **kw)

def err(message, **kw):
    log.err(message, **kw)

# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

import sys
import os
import logging

from twisted.python import log as txlog
from twisted.python.logfile import DailyLogFile

from ooni.utils import otime
from ooni import config

# XXX make this a config option
log_file = "/tmp/ooniprobe.log"

log_folder = os.path.join('/', *log_file.split('/')[:-1])
log_filename = log_file.split('/')[-1]
daily_logfile = DailyLogFile(log_filename, log_folder)

def start():
    txlog.msg("Starting OONI on %s (%s UTC)" %  (otime.prettyDateNow(),
                                                 otime.utcPrettyDateNow()))
    logging.basicConfig()
    python_logging = txlog.PythonLoggingObserver()
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

def err(msg, *arg, **kw):
    txlog.err(msg, logLevel=logging.ERROR, *arg, **kw)

def exception(*msg):
    logging.exception(msg)

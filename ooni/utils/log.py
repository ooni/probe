import sys
import os
import logging
import traceback

from twisted.python import log as txlog
from twisted.python import util
from twisted.python.failure import Failure
from twisted.python.logfile import DailyLogFile

from ooni import otime
from ooni.settings import config

## Get rid of the annoying "No route found for
## IPv6 destination warnings":
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)

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
    if config.logging:
        print "%s" % msg

def debug(msg, *arg, **kw):
    if config.advanced.debug and config.logging:
        print "[D] %s" % msg

def err(msg, *arg, **kw):
    if config.logging:
        print "[!] %s" % msg

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

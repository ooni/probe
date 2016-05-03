import os
import sys
import codecs
import logging
import traceback

from twisted.python import log as txlog
from twisted.python import util
from twisted.python.failure import Failure
from twisted.python.logfile import DailyLogFile

from ooni import otime

# Get rid of the annoying "No route found for
# IPv6 destination warnings":
logging.getLogger("scapy.runtime").setLevel(logging.ERROR)


def log_encode(logmsg):
    """
    I encode logmsg (a str or unicode) as printable ASCII. Each case
    gets a distinct prefix, so that people differentiate a unicode
    from a utf-8-encoded-byte-string or binary gunk that would
    otherwise result in the same final output.
    """
    if isinstance(logmsg, unicode):
        return codecs.encode(logmsg, 'unicode_escape')
    elif isinstance(logmsg, str):
        try:
            unicodelogmsg = logmsg.decode('utf-8')
        except UnicodeDecodeError:
            return codecs.encode(logmsg, 'string_escape')
        else:
            return codecs.encode(unicodelogmsg, 'unicode_escape')
    else:
        raise Exception("I accept only a unicode object or a string, "
                        "not a %s object like %r" % (type(logmsg),
                                                     repr(logmsg)))


class LogWithNoPrefix(txlog.FileLogObserver):
    def emit(self, eventDict):
        text = txlog.textFromEventDict(eventDict)
        if text is None:
            return

        util.untilConcludes(self.write, "%s\n" % text)
        util.untilConcludes(self.flush)  # Hoorj!


class OONILogger(object):
    def start(self, logfile=None, application_name="ooniprobe"):
        from ooni.settings import config

        if not logfile:
            logfile = os.path.expanduser(config.basic.logfile)

        log_folder = os.path.dirname(logfile)
        log_filename = os.path.basename(logfile)

        daily_logfile = DailyLogFile(log_filename, log_folder)

        txlog.msg("Starting %s on %s (%s UTC)" % (application_name,
                                                  otime.prettyDateNow(),
                                                  otime.prettyDateNowUTC()))

        self.fileObserver = txlog.FileLogObserver(daily_logfile)
        self.stdoutObserver = LogWithNoPrefix(sys.stdout)

        txlog.startLoggingWithObserver(self.stdoutObserver.emit)
        txlog.addObserver(self.fileObserver.emit)

    def stop(self):
        self.stdoutObserver.stop()
        self.fileObserver.stop()

oonilogger = OONILogger()


def start(logfile=None, application_name="ooniprobe"):
    oonilogger.start(logfile, application_name)


def stop():
    oonilogger.stop()


def msg(msg, *arg, **kw):
    from ooni.settings import config
    if config.logging:
        print "%s" % log_encode(msg)


def debug(msg, *arg, **kw):
    from ooni.settings import config
    if config.advanced.debug and config.logging:
        print "[D] %s" % log_encode(msg)


def err(msg, *arg, **kw):
    from ooni.settings import config
    if config.logging:
        if isinstance(msg, Exception):
            msg = "%s: %s" % (msg.__class__.__name__, msg)
        print "[!] %s" % log_encode(msg)


def exception(error):
    """
    Error can either be an error message to print to stdout and to the logfile
    or it can be a twisted.python.failure.Failure instance.
    """
    if isinstance(error, Failure):
        error.printTraceback(sys.stdout)
    else:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_exception(exc_type, exc_value, exc_traceback)

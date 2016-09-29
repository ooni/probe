import os
import sys
import errno
import codecs
import logging
from datetime import datetime

from twisted.python import log as tw_log
from twisted.python.logfile import DailyLogFile

from ooni.utils import mkdir_p
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


levels = {
    'NONE': 9999,
    'CRITICAL': 50,
    'ERROR': 40,
    'WARNING': 30,
    # This is the name twisted gives it
    'WARN': 30,
    'NOTICE': 25,
    'INFO': 20,
    'DEBUG': 10,
}

class LogLevelObserver(tw_log.FileLogObserver):
    def __init__(self, f, log_level=levels['INFO']):
        tw_log.FileLogObserver.__init__(self, f)
        self.log_level = log_level

    def should_emit(self, eventDict):
        if eventDict['isError']:
            level = levels['ERROR']
        elif 'log_level' in eventDict:
            level = eventDict['log_level']
        else:
            level = levels['INFO']

        # To support twisted > 15.2 log_level argument
        if hasattr(level, 'name'):
            level = levels[level.name.upper()]

        source = 'unknown'
        if 'source' in eventDict:
            source = eventDict['source']

        # Don't log messages not coming from OONI unless the configured log
        # level is debug and unless they are really important.
        if (source != 'ooni' and
                level <= levels['WARN'] and
                self.log_level >= levels['DEBUG']):
            return False

        if level >= self.log_level:
            return True
        return False

    def emit(self, eventDict):
        if not self.should_emit(eventDict):
            return
        tw_log.FileLogObserver.emit(self, eventDict)

class StdoutStderrObserver(LogLevelObserver):
    stderr = sys.stderr

    def emit(self, eventDict):
        if not self.should_emit(eventDict):
            return

        text = tw_log.textFromEventDict(eventDict)
        if eventDict['isError']:
            self.stderr.write(text + "\n")
            self.stderr.flush()
        else:
            self.write(text + "\n")
            self.flush()

class MsecLogObserver(tw_log.FileLogObserver):
    def formatTime(self, when):
        """
        Code from Twisted==16.4.1 modified to log microseconds.  Although this
        logging subsystem is legacy: http://twistedmatrix.com/trac/ticket/7596
        Also, `timeFormat` is not used as `%z` is broken.
        """
        tzOffset = -self.getTimezoneOffset(when)
        when = datetime.utcfromtimestamp(when + tzOffset)
        tzHour = abs(int(tzOffset / 60 / 60))
        tzMin = abs(int(tzOffset / 60 % 60))
        if tzOffset < 0:
            tzSign = '-'
        else:
            tzSign = '+'
        return '%d-%02d-%02d %02d:%02d:%02d,%06d%s%02d%02d' % (
            when.year, when.month, when.day,
            when.hour, when.minute, when.second,
            when.microsecond,
            tzSign, tzHour, tzMin)

class OONILogger(object):
    def msg(self, msg, *arg, **kw):
        text = log_encode(msg)
        tw_log.msg(text, log_level=levels['INFO'], source="ooni")

    def debug(self, msg, *arg, **kw):
        text = log_encode(msg)
        tw_log.msg(text, log_level=levels['DEBUG'], source="ooni")

    def err(self, msg, *arg, **kw):
        if isinstance(msg, str) or isinstance(msg, unicode):
            text = "[!] " + log_encode(msg)
            tw_log.msg(text, log_level=levels['ERROR'], source="ooni")
        else:
            tw_log.err(msg, source="ooni")

    def warn(self, msg, *arg, **kw):
        text = log_encode(msg)
        tw_log.msg(text, log_level=levels['WARNING'], source="ooni")

    def exception(self, error):
        """
        Error can either be an error message to print to stdout and to the logfile
        or it can be a twisted.python.failure.Failure instance.
        """
        tw_log.err(error, source="ooni")

    def start(self, logfile=None, application_name="ooniprobe"):
        from ooni.settings import config

        if not logfile:
            logfile = os.path.expanduser(config.basic.logfile)

        log_folder = os.path.dirname(logfile)
        if (not os.access(log_folder, os.W_OK) or
            (os.path.exists(logfile) and not os.access(logfile, os.W_OK))):
            # If we don't have permissions to write to the log_folder or
            # logfile.
            log_folder = config.running_path
            logfile = os.path.join(log_folder, "ooniprobe.log")

        mkdir_p(log_folder)

        log_filename = os.path.basename(logfile)
        file_log_level = levels.get(config.basic.loglevel,
                                    levels['INFO'])
        stdout_log_level = levels['INFO']
        if config.advanced.debug:
            stdout_log_level = levels['DEBUG']

        daily_logfile = DailyLogFile(log_filename, log_folder)

        self.fileObserver = MsecLogObserver(LogLevelObserver(daily_logfile,
                                             log_level=file_log_level))
        self.stdoutObserver = StdoutStderrObserver(sys.stdout,
                                                   log_level=stdout_log_level)

        tw_log.startLoggingWithObserver(self.fileObserver.emit)
        tw_log.addObserver(self.stdoutObserver.emit)

        tw_log.msg("Starting %s on %s (%s UTC)" % (application_name,
                                                   otime.prettyDateNow(),
                                                   otime.prettyDateNowUTC()))

    def stop(self):
        self.stdoutObserver.stop()
        self.fileObserver.stop()

oonilogger = OONILogger()
# This is a mock of a LoggerObserverFactory to be supplied to twistd.
ooniloggerNull = lambda: lambda eventDict: None

start = oonilogger.start
stop = oonilogger.stop

msg = oonilogger.msg
debug = oonilogger.debug
err = oonilogger.err
warn = oonilogger.warn
exception = oonilogger.exception

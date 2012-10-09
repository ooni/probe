"""
OONI logging facility.
"""
from sys                    import stderr, stdout

from twisted.python         import log, util
from twisted.python.failure import Failure

def _get_log_level(level):
    english = ['debug', 'info', 'warn', 'err', 'crit']

    levels = dict(zip(range(len(english)), english))
    number = dict(zip(english, range(len(english))))

    if not level:
        return number['info']
    else:
        ve = "Unknown log level: %s\n" % level
        ve += "Allowed levels: %s\n" % [word for word in english]

        if type(level) is int:
            if 0 <= level <= 4:
                return level
        elif type(level) is str:
            if number.has_key(level.lower()):
                return number[level]
            else:
                raise ValueError, ve
        else:
            raise ValueError, ve

class OONITestFailure(Failure):
    """
    For handling Exceptions asynchronously.

    Can be given an Exception as an argument, else will use the
    most recent Exception from the current stack frame.
    """
    def __init__(self, exception=None, _type=None,
                 _traceback=None, _capture=False):
        Failure.__init__(self, exc_type=_type,
                         exc_tb=_traceback, captureVars=_capture)

class OONILogObserver(log.FileLogObserver):
    """
    Supports logging level verbosity.
    """
    def __init__(self, logfile, verb=None):
        log.FileLogObserver.__init__(self, logfile)
        self.level = _get_log_level(verb) if verb is not None else 1
        assert type(self.level) is int

    def emit(self, eventDict):
        if 'logLevel' in eventDict:
            msgLvl = _get_log_level(eventDict['logLevel'])
            assert type(msgLvl) is int
            ## only log our level and higher
            if self.level <= msgLvl:
                text = log.textFromEventDict(eventDict)
            else:
                text = None
        else:
            text = log.textFromEventDict(eventDict)

        if text is None:
            return

        timeStr = self.formatTime(eventDict['time'])
        fmtDict = {'system': eventDict['system'],
                   'text': text.replace('\n','\n\t')}
        msgStr  = log._safeFormat("[%(system)s] %(text)s\n", fmtDict)

        util.untilConcludes(self.write, timeStr + " " + msgStr)
        util.untilConcludes(self.flush)

def start(logfile=None, verbosity=None):
    if log.defaultObserver:
        verbosity = _get_log_level(verbosity)

        ## Always log to file, keep level at info
        file = open(logfile, 'a') if logfile else stderr
        OONILogObserver(file, "info").start()

        log.msg("Starting OONI...")

def debug(message, level="debug", **kw):
    print "[%s] %s" % (level, message)
    ## If we want debug messages in the logfile:
    #log.msg(message, logLevel=level, **kw)

def msg(message, level="info", **kw):
    log.msg(message, logLevel=level, **kw)

def err(message, level="err", **kw):
    log.err(logLevel=level, **kw)

def warn(message, level="warn", **kw):
    log.msg(logLevel=level, **kw)

def fail(message, exception, level="crit", **kw):
    log.failure(message, OONITestFailure(exception, **kw), logLevel=level)

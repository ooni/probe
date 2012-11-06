"""
In here we define a runner for the oonib backend system.
We are just extending the

"""

from twisted.application import service, internet, app
from twisted.python.runtime import platformType

from ooni.utils import log

class OBaseRunner():
    pass

if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions, \
                                WindowsApplicationRunner

    OBaseRunner = WindowsApplicationRunner
else:
    from twisted.scripts._twistd_unix import ServerOptions, \
                                UnixApplicationRunner
    OBaseRunner = UnixApplicationRunner

OBaseRunner.loggerFactory = log.LoggerFactory

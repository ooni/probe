"""
In here we define a runner for the oonib backend system.
We are just extending the

"""

from twisted.internet import reactor
from twisted.application import service, internet, app
from twisted.python.runtime import platformType

import txtorcon

from oonib.report.api import reportingBackend

from oonib import config
from ooni.utils import log

def txSetupFailed(failure):
    log.err("Setup failed")
    log.exception(failure)

def setupCollector(tor_process_protocol):
    def setup_complete(port):
        print "Exposed collector Tor hidden service on httpo://%s" % port.onion_uri

    torconfig = txtorcon.TorConfig(tor_process_protocol.tor_protocol)
    public_port = 80
    # XXX there is currently a bug in txtorcon that prevents data_dir from
    # being passed properly. Details on the bug can be found here:
    # https://github.com/meejah/txtorcon/pull/22
    hs_endpoint = txtorcon.TCPHiddenServiceEndpoint(reactor, torconfig,
            public_port, data_dir=config.main.tor_datadir)
    hidden_service = hs_endpoint.listen(reportingBackend)
    hidden_service.addCallback(setup_complete)
    hidden_service.addErrback(txSetupFailed)

def startTor():
    def updates(prog, tag, summary):
        print "%d%%: %s" % (prog, summary)

    torconfig = txtorcon.TorConfig()
    torconfig.SocksPort = 9055
    torconfig.save()
    d = txtorcon.launch_tor(torconfig, reactor,
            tor_binary=config.main.tor_binary,
            progress_updates=updates)
    d.addCallback(setupCollector)
    d.addErrback(txSetupFailed)

class OBaseRunner():
    pass

if platformType == "win32":
    from twisted.scripts._twistw import ServerOptions, \
                                WindowsApplicationRunner

    OBaseRunner = WindowsApplicationRunner
    # XXX Current we don't support windows for the starting of Tor Hidden Service

else:
    from twisted.scripts._twistd_unix import ServerOptions, \
                                UnixApplicationRunner
    class OBaseRunner(UnixApplicationRunner):
        def postApplication(self):
            """
            To be called after the application is created: start the
            application and run the reactor. After the reactor stops,
            clean up PID files and such.
            """
            self.startApplication(self.application)
            # This is our addition. The rest is taken from
            # twisted/scripts/_twistd_unix.py 12.2.0
            startTor()
            self.startReactor(None, self.oldstdout, self.oldstderr)
            self.removePID(self.config['pidfile'])

OBaseRunner.loggerFactory = log.LoggerFactory



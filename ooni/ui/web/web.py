import os

from twisted.scripts import twistd
from twisted.python import usage
from twisted.internet import reactor
from twisted.web import server
from twisted.application import service

from ooni.settings import config
from ooni.director import Director
from ooni.utils import log

from .server import TopLevel

class WebUI(service.MultiService):
    portNum = 8822
    def startService(self):
        service.MultiService.startService(self)
        config.set_paths()
        config.initialize_ooni_home()
        config.read_config_file()
        def _started(res):
            log.msg("Director started")
            root = server.Site(TopLevel(config, director))
            self._port = reactor.listenTCP(self.portNum, root)
        director = Director()
        d = director.start()
        d.addCallback(_started)
        d.addErrback(self._startupFailed)

    def _startupFailed(self, err):
        log.err("Failed to start the director")
        log.exception(err)
        os.abort()

    def stopService(self):
        if self._port:
            self._port.stopListening()

class StartOoniprobeWebUIPlugin:
    tapname = "ooniprobe"
    def makeService(self, so):
        return WebUI()

class OoniprobeTwistdConfig(twistd.ServerOptions):
    subCommands = [("StartOoniprobeWebUI", None, usage.Options, "ooniprobe web ui")]

def start():
    twistd_args = ["--nodaemon"]
    twistd_config = OoniprobeTwistdConfig()
    twistd_args.append("StartOoniprobeWebUI")
    try:
        twistd_config.parseOptions(twistd_args)
    except usage.error, ue:
        print("ooniprobe: usage error from twistd: {}\n".format(ue))
    twistd_config.loadedPlugins = {"StartOoniprobeWebUI": StartOoniprobeWebUIPlugin()}
    twistd.runApp(twistd_config)
    return 0

if __name__ == "__main__":
    start()

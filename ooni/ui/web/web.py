from twisted.web import server
from twisted.internet import reactor
from twisted.application import service

from ooni.ui.web.server import WebUIAPI
from ooni.settings import config

class WebUIService(service.MultiService):
    def __init__(self, director, scheduler, port_number=8842):
        service.MultiService.__init__(self)

        self.director = director
        self.scheduler = scheduler
        self.port_number = port_number

    def startService(self):
        service.MultiService.startService(self)

        web_ui_api = WebUIAPI(config, self.director, self.scheduler)
        self._port = reactor.listenTCP(
            self.port_number,
            server.Site(web_ui_api.app.resource()),
            interface=config.advanced.webui_address
        )

    def stopService(self):
        service.MultiService.stopService(self)
        if self._port:
            self._port.stopListening()

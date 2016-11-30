from twisted.web import server
from twisted.internet import reactor
from twisted.application import service

from ooni.ui.web.server import WebUIAPI
from ooni.settings import config

class WebUIService(service.MultiService):
    """Contain any element to manage the web user interface service.


    The class above inherits to another class wich is a services container."""

    def __init__(self, director, scheduler, port_number=8842):
        service.MultiService.__init__(self)

        self.director = director
        self.scheduler = scheduler
        self.port_number = port_number

    def startService(self):
        """Start a web user interface.

        Connects a given protocol factory to the given numeric TCP/IP port and open a page."""

        service.MultiService.startService(self)

        web_ui_api = WebUIAPI(config, self.director, self.scheduler)
        self._port = reactor.listenTCP(
            self.port_number,
            server.Site(web_ui_api.app.resource()),
            interface=config.advanced.webui_address
            )

    def stopService(self):
        """Close the web page.

        Close the service, verify that the connection is really finished. If the program is still listenning, the program kill the connection."""
        service.MultiService.stopService(self)
        if self._port:
            self._port.stopListening()

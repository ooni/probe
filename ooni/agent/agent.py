from twisted.application import service
from ooni.director import Director
from ooni.settings import config

from ooni.ui.web.web import WebUIService
from ooni.agent.scheduler import SchedulerService

class AgentService(service.MultiService):
    """Manage agent services."""


    def __init__(self, web_ui_port):
        """Load configuration or made the default configuration of the service.


        If the advanced configuration is not enabled, the page is not displayed.
        Else, if the advanced configuration is enabled, the page is displayed."""

        service.MultiService.__init__(self)
        director = Director()

        self.scheduler_service = SchedulerService(director)
        self.scheduler_service.setServiceParent(self)

        if not config.advanced.disabled_webui:
            self.web_ui_service = WebUIService(director,
                                               self.scheduler_service,
                                               web_ui_port)
            self.web_ui_service.setServiceParent(self)


    def startService(self):
        """Run a service."""

        service.MultiService.startService(self)

    def stopService(self):
        """Kill a service."""

        service.MultiService.stopService(self)

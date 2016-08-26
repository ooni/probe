from twisted.application import service
from ooni.director import Director
from ooni.settings import config

from ooni.ui.web.web import WebUIService
from ooni.agent.scheduler import SchedulerService

class AgentService(service.MultiService):
    def __init__(self, web_ui_port):
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
        service.MultiService.startService(self)

    def stopService(self):
        service.MultiService.stopService(self)

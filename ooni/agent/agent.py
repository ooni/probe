from twisted.application import service
from ooni.director import Director
from ooni.settings import config
from ooni.utils import log

from ooni.ui.web.web import WebUIService
from ooni.agent.scheduler import SchedulerService

class AgentService(service.MultiService):
    def __init__(self):
        service.MultiService.__init__(self)

        director = Director()
        config.set_paths()
        config.initialize_ooni_home()
        config.read_config_file()

        self.web_ui_service = WebUIService(director)
        self.web_ui_service.setServiceParent(self)

        self.scheduler_service = SchedulerService(director)
        self.scheduler_service.setServiceParent(self)

    def startService(self):
        service.MultiService.startService(self)

        log.start()

    def stopService(self):
        service.MultiService.stopService(self)

        log.stop()

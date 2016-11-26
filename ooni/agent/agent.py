from twisted.application import service
from ooni.director import Director
from ooni.settings import config

from ooni.ui.web.web import WebUIService
from ooni.agent.scheduler import SchedulerService

class AgentService(service.MultiService):
    """Contain any element to manage services.



    The class above inherits to another class wich is a services container.
    It gets one parameter: the variable web_ui_port.

    There are potentially three instanciations:
    The element director is an instance of the Director class from the ooni.settings module.
    The element scheduler_service is another instance of the class SchedulerService from the module ooni.agent.schedule.
    And at last but not least, if the advanced configuration of webui is not disabled, there is web_ui_service.
    The web_ui_service is the last instance of the class WebUIService from the module ooni.ui.web.web.
        web_ui_service has three parameters: the director instance, the scheduler_service attribute, and the variable web_ui_port.


    Two functions may be automatically present during the initialization of the code:
    setServiceParent() and if the advanced configuration of webui is not disabled, web_ui_service.setServiceParent() is run.


    Two methods are defined:
      startService() to start a service
      stopService() to kill a service."""


    def __init__(self, web_ui_port):
        """"""
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

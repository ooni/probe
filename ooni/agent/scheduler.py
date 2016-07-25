from twisted.application import service
from twisted.internet import task

class SchedulerService(service.MultiService):
    """
    This service is responsible for running the periodic tasks.
    """
    def __init__(self, director, interval=30):
        service.MultiService.__init__(self)
        self.director = director
        self.interval = interval
        self._looping_call = task.LoopingCall(self._should_run)

    def _should_run(self):
        """
        This function is called every self.interval seconds to check
        which periodic tasks should be run.
        """
        pass

    def startService(self):
        service.MultiService.startService(self)
        self._looping_call.start(self.interval)

    def stopService(self):
        service.MultiService.stopService(self)
        self._looping_call.stop()

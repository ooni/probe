from datetime import datetime

from twisted.application import service
from twisted.internet import task, defer
from twisted.python.filepath import FilePath

from ooni import resources
from ooni.utils import log
from ooni.deck import input_store
from ooni.settings import config
from ooni.contrib import croniter
from ooni.geoip import probe_ip

class ScheduledTask(object):
    _time_format = "%Y-%m-%dT%H:%M:%SZ"
    schedule = None
    identifier = None

    def __init__(self, schedule=None):
        if schedule is not None:
            self.schedule = schedule

        assert self.identifier is not None, "self.identifier must be set"
        assert self.schedule is not None, "self.schedule must be set"
        scheduler_directory = config.scheduler_directory

        self._last_run = FilePath(scheduler_directory).child(self.identifier)
        self._last_run_lock = defer.DeferredFilesystemLock(
            FilePath(scheduler_directory).child(self.identifier + ".lock").path
        )

    @property
    def should_run(self):
        current_time = datetime.utcnow()
        next_cycle = croniter(self.schedule, self.last_run).get_next(datetime)
        if next_cycle <= current_time:
            return True
        return False

    @property
    def last_run(self):
        if not self._last_run.exists():
            return datetime.fromtimestamp(0)
        with self._last_run.open('r') as in_file:
            date_str = in_file.read()
        return datetime.strptime(date_str, self._time_format)

    def _update_last_run(self):
        with self._last_run.open('w') as out_file:
            current_time = datetime.utcnow()
            out_file.write(current_time.strftime(self._time_format))

    def task(self):
        raise NotImplemented

    @defer.inlineCallbacks
    def run(self):
        yield self._last_run_lock.deferUntilLocked()
        if not self.should_run:
            self._last_run_lock.unlock()
            defer.returnValue(None)
        try:
            yield self.task()
            self._update_last_run()
        except:
            raise
        finally:
            self._last_run_lock.unlock()

class UpdateInputsAndResources(ScheduledTask):
    identifier = "ooni-update-inputs"
    schedule = "@daily"

    @defer.inlineCallbacks
    def task(self):
        log.debug("Updating the inputs")
        yield probe_ip.lookup()
        yield resources.check_for_update(probe_ip.geodata['countrycode'])
        yield input_store.update(probe_ip.geodata['countrycode'])

class CleanupInProgressReports(ScheduledTask):
    identifier = 'ooni-cleanup-reports'
    schedule = '@daily'

class UploadMissingReports(ScheduledTask):
    identifier = 'ooni-cleanup-reports'
    schedule = '@weekly'

# Order mattters
SYSTEM_TASKS = [
    UpdateInputsAndResources
]

@defer.inlineCallbacks
def run_system_tasks(no_input_store=False):
    task_classes = SYSTEM_TASKS[:]

    if no_input_store:
        log.debug("Not updating the inputs")
        task_classes.pop(UpdateInputsAndResources)

    for task_class in task_classes:
        task = task_class()
        log.debug("Running task {0}".format(task.identifier))
        try:
            yield task.run()
        except Exception as exc:
            log.err("Failed to run task {0}".format(task.identifier))
            log.exception(exc)

class SchedulerService(service.MultiService):
    """
    This service is responsible for running the periodic tasks.
    """
    def __init__(self, director, interval=30):
        service.MultiService.__init__(self)
        self.director = director
        self.interval = interval
        self._looping_call = task.LoopingCall(self._should_run)
        self._scheduled_tasks = []

    def schedule(self, task):
        self._scheduled_tasks.append(task)

    def _task_failed(self, failure, task):
        log.debug("Failed to run {0}".format(task.identifier))
        log.exception(failure)

    def _task_success(self, result, task):
        log.debug("Ran {0}".format(task.identifier))

    def _should_run(self):
        """
        This function is called every self.interval seconds to check
        which periodic tasks should be run.
        """
        for task in self._scheduled_tasks:
            log.debug("Running task {0}".format(task.identifier))
            d = task.run()
            d.addErrback(self._task_failed, task)
            d.addCallback(self._task_success, task)

    def startService(self):
        service.MultiService.startService(self)

        self.schedule(UpdateInputsAndResources())

        self._looping_call.start(self.interval)

    def stopService(self):
        service.MultiService.stopService(self)
        self._looping_call.stop()

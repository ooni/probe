from datetime import datetime

from twisted.application import service
from twisted.internet import defer
from twisted.internet.task import LoopingCall
from twisted.python.filepath import FilePath

from ooni.scripts import oonireport
from ooni import resources
from ooni.utils import log, SHORT_DATE
from ooni.deck.store import input_store, deck_store
from ooni.settings import config
from ooni.contrib import croniter
from ooni.geoip import probe_ip
from ooni.measurements import list_measurements

class FileSystemlockAndMutex(object):
    """
    This is a lock that is both a mutex lock and also on filesystem.
    When you acquire it, it will first block on the mutex lock and then
    once that is released it will attempt to acquire the lock on the
    filesystem.

    It's a way to support concurrent usage of the DeferredFilesystemLock
    without races.
    """
    def __init__(self, file_path):
        self._fs_lock = defer.DeferredFilesystemLock(file_path)
        self._mutex = defer.DeferredLock()

    @defer.inlineCallbacks
    def acquire(self):
        yield self._mutex.acquire()
        yield self._fs_lock.deferUntilLocked()

    def release(self):
        self._fs_lock.unlock()
        self._mutex.release()

class DidNotRun(Exception):
    pass

class ScheduledTask(object):
    _time_format = "%Y-%m-%dT%H:%M:%SZ"
    schedule = None
    identifier = None

    def __init__(self, schedule=None, identifier=None):
        if schedule is not None:
            self.schedule = schedule
        if identifier is not None:
            self.identifier = identifier

        assert self.identifier is not None, "self.identifier must be set"
        assert self.schedule is not None, "self.schedule must be set"
        scheduler_directory = config.scheduler_directory

        self._last_run = FilePath(scheduler_directory).child(self.identifier)
        self._last_run_lock = FileSystemlockAndMutex(
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
        yield self._last_run_lock.acquire()
        if not self.should_run:
            self._last_run_lock.release()
            raise DidNotRun
        try:
            yield self.task()
            self._update_last_run()
        except:
            raise
        finally:
            self._last_run_lock.release()


class UpdateInputsAndResources(ScheduledTask):
    identifier = "update-inputs"
    schedule = "@daily"

    @defer.inlineCallbacks
    def task(self):
        log.debug("Updating the inputs")
        yield probe_ip.lookup()
        yield resources.check_for_update(probe_ip.geodata['countrycode'])
        yield input_store.update(probe_ip.geodata['countrycode'])
        yield probe_ip.resolveGeodata()


class UploadReports(ScheduledTask):
    """
    This task is used to submit to the collector reports that have not been
    submitted and those that have been partially uploaded.
    """
    identifier = 'upload-reports'
    schedule = '@hourly'

    @defer.inlineCallbacks
    def task(self):
        yield oonireport.upload_all(upload_incomplete=True)


class DeleteOldReports(ScheduledTask):
    """
    This task is used to delete reports that are older than a week.
    """
    identifier = 'delete-old-reports'
    schedule = '@daily'

    def task(self):
        measurement_path = FilePath(config.measurements_directory)
        for measurement in list_measurements():
            if measurement['keep'] is True:
                continue
            delta = datetime.utcnow() - \
                    datetime.strptime(measurement['test_start_time'],
                                      SHORT_DATE)
            if delta.days >= 7:
                log.debug("Deleting old report {0}".format(measurement["id"]))
                measurement_path.child(measurement['id']).remove()


class RunDeck(ScheduledTask):
    """
    This will run the decks that have been configured on the system as the
    decks to run by default.
    """

    def __init__(self, director, deck_id, schedule):
        self.deck_id = deck_id
        self.director = director
        identifier = 'run-deck-' + deck_id
        super(RunDeck, self).__init__(schedule, identifier)

    @defer.inlineCallbacks
    def task(self):
        deck = deck_store.get(self.deck_id)
        yield deck.setup()
        yield deck.run(self.director)


class RefreshDeckList(ScheduledTask):
    """
    This task is configured to refresh the list of decks that are enabled.
    """
    identifier = 'refresh-deck-list'
    schedule = '@hourly'

    def __init__(self, scheduler, schedule=None, identifier=None):
        self.scheduler = scheduler
        super(RefreshDeckList, self).__init__(schedule, identifier)

    def task(self):
        self.scheduler.refresh_deck_list()

class SendHeartBeat(ScheduledTask):
    """
    This task is used to send a heartbeat that the probe is still alive and
    well.
    """
    identifier = 'send-heartbeat'
    schedule = '@hourly'

    def task(self):
        # XXX implement this
        pass

# Order mattters
SYSTEM_TASKS = [
    UpdateInputsAndResources
]

@defer.inlineCallbacks
def run_system_tasks(no_input_store=False):
    task_classes = SYSTEM_TASKS[:]

    if no_input_store:
        log.debug("Not updating the inputs")
        task_classes.remove(UpdateInputsAndResources)

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
        self._looping_call = LoopingCall(self._should_run)
        self._scheduled_tasks = []

    def schedule(self, task):
        self._scheduled_tasks.append(task)

    def refresh_deck_list(self):
        # Deletes all the RunDeck tasks and reschedules only the ones that
        # are enabled.
        for scheduled_task in self._scheduled_tasks[:]:
            if isinstance(scheduled_task, RunDeck):
                self._scheduled_tasks.remove(scheduled_task)

        for deck_id, deck in deck_store.list_enabled():
            if deck.schedule is None:
                continue
            self.schedule(RunDeck(self.director, deck_id, deck.schedule))

    def _task_did_not_run(self, failure, task):
        failure.trap(DidNotRun)
        log.debug("Did not run {0}".format(task.identifier))

    def _task_failed(self, failure, task):
        log.err("Failed to run {0}".format(task.identifier))
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
            d.addErrback(self._task_did_not_run, task)
            d.addCallback(self._task_success, task)
            d.addErrback(self._task_failed, task)

    def startService(self):
        service.MultiService.startService(self)

        self.refresh_deck_list()
        self.schedule(UpdateInputsAndResources())
        self.schedule(UploadReports())
        self.schedule(DeleteOldReports())
        self.schedule(RefreshDeckList(self))

        self._looping_call.start(self.interval)

    def stopService(self):
        service.MultiService.stopService(self)
        self._looping_call.stop()

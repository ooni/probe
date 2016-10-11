import os
import errno

from hashlib import md5
from datetime import datetime

from twisted.application import service
from twisted.internet import defer, reactor
from twisted.internet.task import LoopingCall
from twisted.python.filepath import FilePath

from ooni.scripts import oonireport
from ooni import resources
from ooni.utils import log, SHORT_DATE
from ooni.utils.files import human_size_to_bytes, directory_usage
from ooni.deck.store import input_store, deck_store, DEFAULT_DECKS
from ooni.settings import config
from ooni.contrib import croniter
from ooni.contrib.dateutil.tz import tz

from ooni.geoip import probe_ip
from ooni.measurements import list_measurements

class FileSystemlockAndMutex(object):
    """
    This is a lock that is both a mutex lock and also on filesystem.
    When you acquire it, it will first acquire the mutex lock and then
    acquire the filesystem lock. The release order is inverted.

    This is to avoid concurrent usage within the same process. When using it
    concurrently the mutex lock will block before the filesystem lock is
    acquired.

    It's a way to support concurrent usage of the DeferredFilesystemLock from
    different stacks (threads/fibers) within the same process without races.
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

    @property
    def locked(self):
        return self._mutex.locked or self._fs_lock.locked

# We use this date to indicate that the scheduled task has never run.
# Easter egg, try to see what is special about this date :)?
CANARY_DATE = datetime(1957, 10, 4, tzinfo=tz.tzutc())


class DidNotRun(Exception):
    pass


class ScheduledTask(object):
    """
    Two ScheduledTask instances with same identifier are not permited to run
    concurrently.  There should be no ScheduledTask queue waiting for the lock
    as SchedulerService ticks quite often.
    """
    _time_format = "%Y-%m-%dT%H:%M:%SZ"
    schedule = None
    identifier = None

    def __init__(self, schedule=None, identifier=None,
                 scheduler_directory=None):
        if scheduler_directory is None:
            scheduler_directory = config.scheduler_directory
        if schedule is not None:
            self.schedule = schedule
        if identifier is not None:
            self.identifier = identifier

        assert self.identifier is not None, "self.identifier must be set"
        assert self.schedule is not None, "self.schedule must be set"

        self._last_run = FilePath(scheduler_directory).child(self.identifier)
        self._last_run_lock = FileSystemlockAndMutex(
            FilePath(scheduler_directory).child(self.identifier + ".lock").path
        )

    def cancel(self):
        self._last_run_lock.release()

    @property
    def should_run(self):
        current_time = datetime.utcnow().replace(tzinfo=tz.tzutc())
        next_cycle = croniter(self.schedule, self.last_run).get_next(datetime)
        if next_cycle <= current_time:
            return True
        return False

    @property
    def last_run(self):
        self._last_run.restat(False)
        if not self._last_run.exists():
            return CANARY_DATE
        with self._last_run.open('r') as in_file:
            date_str = in_file.read()
        return datetime.strptime(date_str, self._time_format).replace(
            tzinfo=tz.tzutc())

    def _update_last_run(self, last_run_time):
        with self._last_run.open('w') as out_file:
            out_file.write(last_run_time.strftime(self._time_format))

    def task(self):
        raise NotImplementedError

    def first_run(self):
        """
        This hook is called if it's the first time a particular scheduled
        operation is run.
        """
        pass

    @defer.inlineCallbacks
    def run(self):
        if self._last_run_lock.locked:
            # do not allow the queue to grow forever
            raise DidNotRun
        yield self._last_run_lock.acquire()
        if not self.should_run:
            self._last_run_lock.release()
            raise DidNotRun
        try:
            if self.last_run == CANARY_DATE:
                log.debug("Detected first run")
                yield defer.maybeDeferred(self.first_run)
            last_run_time = datetime.utcnow()
            yield self.task()
            self._update_last_run(last_run_time)
        except:
            raise
        finally:
            self._last_run_lock.release()


class UpdateInputsAndResources(ScheduledTask):
    identifier = "update-inputs"
    schedule = "@daily"

    @defer.inlineCallbacks
    def first_run(self):
        """
        On first run we update the resources that are common to every country.
        """
        log.debug("Updating the global inputs and resources")
        yield resources.check_for_update("ZZ")

    @defer.inlineCallbacks
    def task(self):
        log.debug("Updating the inputs")
        yield probe_ip.lookup()
        log.debug("Updating the inputs for country %s" %
                  probe_ip.geodata['countrycode'])
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


class CheckMeasurementQuota(ScheduledTask):
    """
    This task is run to ensure we don't run out of disk space and deletes
    older reports to avoid filling the quota.
    """
    identifier = 'check-measurement-quota'
    schedule = '@hourly'
    _warn_when = 0.8

    def task(self):
        if config.basic.measurement_quota is None:
            return
        maximum_bytes = human_size_to_bytes(config.basic.measurement_quota)
        used_bytes = directory_usage(config.measurements_directory)
        warning_path = os.path.join(config.running_path, 'quota_warning')

        if (float(used_bytes) / float(maximum_bytes)) >= self._warn_when:
            log.warn("You are about to reach the maximum allowed quota. Be careful")
            with open(warning_path, "w") as out_file:
                out_file.write("{0} {1}".format(used_bytes,
                                                maximum_bytes))
        else:
            try:
                os.remove(warning_path)
            except OSError as ose:
                if ose.errno != errno.ENOENT:
                    raise

        if float(used_bytes) < float(maximum_bytes):
            # We are within the allow quota exit.
            return

        # We should begin to delete old reports
        amount_to_delete = float(used_bytes) - float(maximum_bytes)
        amount_deleted = 0
        measurement_path = FilePath(config.measurements_directory)

        kept_measurements = []
        stale_measurements = []
        remaining_measurements = []
        measurements_by_date = sorted(list_measurements(compute_size=True),
                                      key=lambda k: k['test_start_time'])
        for measurement in measurements_by_date:
            if measurement['keep'] is True:
                kept_measurements.append(measurement)
            elif measurement['stale'] is True:
                stale_measurements.append(measurement)
            else:
                remaining_measurements.append(measurement)

        # This is the order in which we should begin deleting measurements.
        ordered_measurements = (stale_measurements +
                                remaining_measurements +
                                kept_measurements)
        while amount_deleted < amount_to_delete:
            measurement = ordered_measurements.pop(0)
            log.warn("Deleting report {0}".format(measurement["id"]))
            measurement_path.child(measurement['id']).remove()
            amount_deleted += measurement['size']


class RunDeck(ScheduledTask):
    """
    This will run the decks that have been configured on the system as the
    decks to run by default.
    """

    def __init__(self, director, deck_id, schedule):
        self.deck_id = deck_id
        self.director = director
        # We use as identifier also the schedule time
        identifier = 'run-deck-' + deck_id + '-' + md5(schedule).hexdigest()
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

    def first_run(self):
        """
        On first run we enable the default decks.
        """
        for deck_id in DEFAULT_DECKS:
            deck_store.enable(deck_id)

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

# Order matters
SYSTEM_TASKS = [
    UpdateInputsAndResources
]


@defer.inlineCallbacks
def run_system_tasks(no_input_store=False):
    task_classes = SYSTEM_TASKS[:]

    if no_input_store:
        log.debug("Not updating the inputs")
        try:
            task_classes.remove(UpdateInputsAndResources)
        except ValueError:
            pass

    for task_class in task_classes:
        task = task_class()
        log.debug("Running task {0}".format(task.identifier))
        try:
            yield task.run()
        except DidNotRun:
            log.debug("Did not run {0}".format(task.identifier))
        except Exception as exc:
            log.err("Failed to run task {0}".format(task.identifier))
            log.exception(exc)


class SchedulerService(service.MultiService):
    """
    This service is responsible for running the periodic tasks.
    """
    def __init__(self, director, interval=30, _reactor=reactor):
        service.MultiService.__init__(self)
        self.director = director
        self.interval = interval

        self._looping_call = LoopingCall(self._should_run)
        self._looping_call.clock = _reactor

        self._scheduled_tasks = []

    def schedule(self, task):
        self._scheduled_tasks.append(task)

    def unschedule(self, task):
        # We first cancel the task so the run lock is deleted
        task.cancel()
        self._scheduled_tasks.remove(task)

    def refresh_deck_list(self):
        """
        This checks if there are some decks that have been enabled and
        should be scheduled as periodic tasks to run on the next scheduler
        cycle and if some have been disabled and should not be run.

        It does so by listing the enabled decks and checking if the enabled
        ones are already scheduled or if some of the scheduled ones are not
        amongst the enabled decks.
        """
        to_enable = []
        for deck_id, deck in deck_store.list_enabled():
            if deck.schedule is None:
                continue
            to_enable.append((deck_id, deck.schedule))

        # If we are not initialized we should not enable anything
        if not config.is_initialized():
            log.msg("We are not initialized skipping setup of decks")
            to_enable = []

        for scheduled_task in self._scheduled_tasks[:]:
            if not isinstance(scheduled_task, RunDeck):
                continue

            info = (scheduled_task.deck_id, scheduled_task.schedule)
            if info in to_enable:
                # If the task is already scheduled there is no need to
                # enable it.
                log.msg("The deck {0} is already scheduled".format(deck_id))
                to_enable.remove(info)
            else:
                # If one of the tasks that is scheduled is no longer in the
                # scheduled tasks. We should disable it.
                log.msg("The deck task {0} should be disabled".format(deck_id))
                self.unschedule(scheduled_task)

        for deck_id, schedule in to_enable:
            log.msg("Scheduling to run {0}".format(deck_id))
            self.schedule(RunDeck(self.director, deck_id, schedule))

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

        Note: the task will wait on the lock if there is already a task of
        that type running. This means that if a task is very long running
        there can potentially be a pretty large backlog of accumulated
        periodic tasks waiting to know if they should run.
        XXX
        We may want to do something like not wait on the lock if there is
        already a queue that is larger than a certain amount or something
        smarter if still starts to become a memory usage concern.
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
        self.schedule(CheckMeasurementQuota())
        self.schedule(RefreshDeckList(self))

        self._looping_call.start(self.interval)

    def stopService(self):
        service.MultiService.stopService(self)
        self._looping_call.stop()

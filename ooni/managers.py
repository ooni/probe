import itertools
from twisted.internet import defer

from ooni.utils import log
from ooni.settings import config


def makeIterable(item):
    """
    Takes as argument or an iterable and if it's not an iterable object then it
    will return a listiterator.
    """
    try:
        iterable = iter(item)
    except TypeError:
        iterable = iter([item])
    return iterable


class TaskManager(object):
    retries = 2
    concurrency = 10

    def __init__(self):
        self._tasks = iter(())
        self._active_tasks = []
        self.failures = 0
        self.task_lock = defer.DeferredLock()

    def _failed(self, failure, task):
        """
        The has failed to complete, we append it to the end of the task chain
        to be re-run once all the currently scheduled tasks have run.
        """
        log.debug("Task %s has failed %s times" % (task, task.failures))
        if config.advanced.debug:
            log.exception(failure)

        self._active_tasks.remove(task)
        self.failures = self.failures + 1

        if task.failures <= self.retries:
            log.debug("Rescheduling...")
            self._tasks = itertools.chain(makeIterable(task), self._tasks)

        else:
            # This fires the errback when the task is done but has failed.
            log.debug('Permanent failure for %s' % task)
            task.done.errback(failure)

        self._fillSlots()

        self.failed(failure, task)

    def _fillSlots(self):
        """
        Called on test completion and schedules measurements to be run for the
        available slots.
        """
        d = self.task_lock.acquire()
        d.addCallback(lambda _: self._scheduleNextTask())

    def _scheduleNextTask(self):
        for _ in range(self.availableSlots):
            try:
                task = next(self._tasks)
                self._run(task)
            except StopIteration:
                break
        self.task_lock.release()

    def _run(self, task):
        """
        This gets called to add a task to the list of currently active and
        running tasks.
        """
        self._active_tasks.append(task)

        d = task.start()
        d.addCallback(self._succeeded, task)
        d.addErrback(self._failed, task)

    def _succeeded(self, result, task):
        """
        We have successfully completed a measurement.
        """
        self._active_tasks.remove(task)

        # Fires the done deferred when the task has completed
        task.done.callback(result)

        self._fillSlots()

        self.succeeded(result, task)

    @property
    def failedMeasurements(self):
        return self.failures

    @property
    def availableSlots(self):
        """
        Returns the number of available slots for running tests.
        """
        return self.concurrency - len(self._active_tasks)

    def schedule(self, task_or_task_iterator):
        """
        Takes as argument a single task or a task iterable and appends it to
        the task generator queue.
        """
        log.debug("Starting this task %s" % repr(task_or_task_iterator))

        iterable = makeIterable(task_or_task_iterator)

        self._tasks = itertools.chain(self._tasks, iterable)
        self._fillSlots()

    def start(self):
        """
        This is called to start the task manager.
        """
        self.failures = 0

        self._fillSlots()

    def failed(self, failure, task):
        """
        This hoook is called every time a task has failed.

        The default failure handling logic is to reschedule the task up until
        we reach the maximum number of retries.
        """
        raise NotImplemented

    def succeeded(self, result, task):
        """
        This hook is called every time a task has been successfully executed.
        """
        raise NotImplemented


class LinkedTaskManager(TaskManager):

    def __init__(self):
        super(LinkedTaskManager, self).__init__()
        self.child = None
        self.parent = None

    @property
    def availableSlots(self):
        mySlots = self.concurrency - len(self._active_tasks)
        if self.child:
            s = self.child.availableSlots
            return min(s, mySlots)
        return mySlots

    def _succeeded(self, result, task):
        super(LinkedTaskManager, self)._succeeded(result, task)
        if self.parent:
            self.parent._fillSlots()

    def _failed(self, result, task):
        super(LinkedTaskManager, self)._failed(result, task)
        if self.parent:
            self.parent._fillSlots()


class MeasurementManager(LinkedTaskManager):

    """
    This is the Measurement Tracker. In here we keep track of active
    measurements and issue new measurements once the active ones have been
    completed.

    MeasurementTracker does not keep track of the typology of measurements that
    it is running. It just considers a measurement something that has an input
    and a method to be called.

    NetTest on the contrary is aware of the typology of measurements that it is
    dispatching as they are logically grouped by test file.
    """

    def __init__(self):
        if config.advanced.measurement_retries:
            self.retries = config.advanced.measurement_retries
        if config.advanced.measurement_concurrency:
            self.concurrency = config.advanced.measurement_concurrency
        super(MeasurementManager, self).__init__()

    def succeeded(self, result, measurement):
        log.debug("Successfully performed measurement %s" % measurement)
        log.debug("%s" % result)

    def failed(self, failure, measurement):
        pass


class ReportEntryManager(LinkedTaskManager):

    def __init__(self):
        if config.advanced.reporting_retries:
            self.retries = config.advanced.reporting_retries
        if config.advanced.reporting_concurrency:
            self.concurrency = config.advanced.reporting_concurrency
        super(ReportEntryManager, self).__init__()

    def succeeded(self, result, task):
        log.debug("Successfully performed report %s" % task)
        log.debug(str(result))

    def failed(self, failure, task):
        pass

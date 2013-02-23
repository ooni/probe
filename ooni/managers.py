import itertools
from twisted.internet import defer

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
        self.failures = []

    def _failed(self, failure, task):
        # XXX INFINITE RECURSION LOOP INSIDE OF THIS THING
        """
        The has failed to complete, we append it to the end of the task chain
        to be re-run once all the currently scheduled tasks have run.
        """
        self._active_tasks.remove(task)
        self.failures.append((failure, task))

        if task.failures <= self.retries:
            self._tasks = itertools.chain(self._tasks,
                    makeIterable(task))
        else:
            # This fires the errback when the task is done but has failed.
            task.done.errback(failure)

        self._fillSlots()

        self.failed(failure, task)

    def _fillSlots(self):
        """
        Called on test completion and schedules measurements to be run for the
        available slots.
        """
        for _ in range(self.availableSlots):
            try:
                task = self._tasks.next()
                self._run(task)
            except StopIteration:
                break

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

        self._fillSlots()

        # Fires the done deferred when the task has completed
        task.done.callback(task)
        self.succeeded(result, task)

    @property
    def failedMeasurements(self):
        return len(self.failures)

    @property
    def availableSlots(self):
        """
        Returns the number of available slots for running tests.
        """
        return self.concurrency - len(self._active_tasks)

    def schedule(self, task_or_task_iterator):
        """
        Takes as argument a single task or a task iterable and appends it to the task
        generator queue.
        """
        iterable = makeIterable(task_or_task_iterator)

        self._tasks = itertools.chain(self._tasks, iterable)
        self._fillSlots()

    def start(self):
        """
        This is called to start the task manager.
        """
        self.failures = []

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

class MeasurementManager(TaskManager):
    """
    This is the Measurement Tracker. In here we keep track of active measurements
    and issue new measurements once the active ones have been completed.

    MeasurementTracker does not keep track of the typology of measurements that
    it is running. It just considers a measurement something that has an input
    and a method to be called.

    NetTest on the contrary is aware of the typology of measurements that it is
    dispatching as they are logically grouped by test file.
    """
    # XXX tweak these values
    retries = 2
    concurrency = 10

    def succeeded(self, result, measurement):
        pass

    def failed(self, failure, measurement):
        pass

class ReportEntryManager(TaskManager):
    # XXX tweak these values
    retries = 3
    concurrency = 20

    def succeeded(self, result, task):
        pass

    def failed(self, failure, task):
        pass


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

    failures = []
    concurrency = 10

    completedTasks = 0

    _tasks = iter(())
    _active_tasks = []

    def _failed(self, failure, task):
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
            task.done.callback((failure, task))

        self.failed(failure, task)

        self._fillSlots()

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

    def _succeeded(self, result, task):
        """
        We have successfully completed a measurement.
        """
        self._active_tasks.remove(task)
        self.completedTasks += 1

        self._fillSlots()

        task.done.callback(result)

        self.succeeded(result, task)

    def _run(self, task):
        """
        This gets called to add a task to the list of currently active and
        running tasks.
        """
        self._active_tasks.append(task)

        d = task.start()
        d.addCallback(self._succeeded, task)
        d.addErrback(self._failed, task)

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
        self.failures = []

        self.tasksDone = defer.Deferred()
        self._fillSlots()

    def failed(self, failure, task):
        """
        This method should be overriden by the subclass and should contains
        logic for dealing with a failure that is subclass specific.

        The default failure handling logic is to reschedule the task up until
        we reach the maximum number of retries.
        """
        raise NotImplemented

    def succeeded(self, result, task):
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
    retries = 2

    failures = []
    concurrency = 10

    director = None

    def succeeded(self, result, measurement):
        self.director.measurementSucceeded(measurement)

    def failed(self, failure, measurement):
        self.director.measurementFailed(failure, measurement)

class Report(object):
    reportEntryManager = None

    def __init__(self, reporters, net_test):
        """
        This will instantiate all the reporters and add them to the list of
        available reporters.

        net_test:
            is a reference to the net_test to which the report object belongs to.
        """
        self.netTest = net_test
        self.reporters = []
        for r in reporters:
            reporter = r()
            self.reporters.append(reporter)

        self.createReports()

    def createReports(self):
        """
        This will create all the reports that need to be created.
        """
        for reporter in self.reporters:
            reporter.createReport()

    def write(self, measurement):
        """
        This will write to all the reporters, by waiting on the created
        callback to fire.
        """
        for reporter in self.reporters:
            @reporter.created.addCallback
            def cb(result):
                report_write_task = ReportWrite(reporter, measurement)
                self.reportEntryManager.schedule(report_write_task)

class ReportEntryManager(object):

    director = None

    def __init__(self, manager, netTests=None):
        self.netTests = netTests if netTests else []
        self.manager = manager

    def addNetTest(self, netTest):
        self.netTests.append(netTest)

    def initializeTaskList(self):
        pass

    def succeeded(self, result, measurement):
        pass

    def failed(self, failure, measurement):
        pass


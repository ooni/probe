import time

from twisted.internet import defer, reactor

class BaseTask(object):
    _timer = None

    def __init__(self, mediator=None):
        """
        If you want to schedule a task multiple times, remember to create fresh
        instances of it.
        """
        self.running = False
        self.failures = 0

        self.startTime = time.time()
        self.runtime = 0

        # This is a deferred that gets called when a test has reached it's
        # final status, this means: all retries have been attempted or the test
        # has successfully executed.
        self.done = defer.Deferred()
        if mediator:
            mediator.created()
            self.done.addCallback(mediator.taskDone)

    def _failed(self, failure):
        self.failures += 1
        self.failed(failure)
        return failure

    def _succeeded(self, result):
        self.runtime = time.time() - self.startTime
        self.succeeded(result)
        return result

    def start(self):
        self.running = self.run()
        self.running.addErrback(self._failed)
        self.running.addCallback(self._succeeded)
        return self.running

    def succeeded(self, result):
        """
        Place here the logic to handle a successful execution of the task.
        """
        pass

    def failed(self, failure):
        """
        Place in here logic to handle failure.
        """
        pass

    def run(self):
        """
        Override this with the logic of your task.
        Must return a deferred.
        """
        pass

class TaskTimedOut(Exception):
    pass

class TaskWithTimeout(BaseTask):
    timeout = 5
    # So that we can test the callLater calls
    clock = reactor

    def _timedOut(self):
        """Internal method for handling timeout failure"""
        self.timedOut()
        self.running.errback(TaskTimedOut)

    def _cancelTimer(self):
        #import pdb; pdb.set_trace()
        if self._timer.active():
            self._timer.cancel()

    def _succeeded(self, result):
        self._cancelTimer()
        return BaseTask._succeeded(self, result)

    def _failed(self, failure):
        self._cancelTimer()
        return BaseTask._failed(self, failure)

    def start(self):
        self._timer = self.clock.callLater(self.timeout, self._timedOut)
        return BaseTask.start(self)

    def timedOut(self):
        """
        Override this with the operations to happen when the task has timed
        out.
        """
        pass

class Measurement(TaskWithTimeout):
    def __init__(self, test_class, test_method, test_input, net_test,
            mediator):
        """
        test_class:
            is the class, subclass of NetTestCase, of the test to be run

        test_method:
            is a string representing the test method to be called to perform
            this measurement

        test_input:
            is the input to the test

        net_test:
            a reference to the net_test object such measurement belongs to.
        """
        self.test_instance = test_class()
        self.test_instance.input = test_input
        self.test_instance.report = {}
        self.test_instance._start_time = time.time()
        self.test_instance._setUp()
        self.test_instance.setUp()
        self.test = getattr(self.test_instance, test_method)

        self.netTest = net_test

        TaskWithTimeout.__init__(self, mediator)

    def succeeded(self, result):
        return self.netTest.succeeded(self)

    def failed(self, failure):
        pass

    def timedOut(self):
        self.netTest.timedOut()

    def run(self):
        d = defer.maybeDeferred(self.test)
        return d

class ReportEntry(TaskWithTimeout):
    def __init__(self, reporter, measurement, task_mediator):
        self.reporter = reporter
        self.measurement = measurement

        TaskWithTimeout.__init__(self, task_mediator)

    def run(self):
        return self.reporter.writeReportEntry(self.measurement)


class TaskMediator(object):
    def __init__(self, allTasksDone):
        """
        This implements a Mediator/Observer pattern to keep track of when Tasks
        that are logically linked together have all reached a final done stage.

        Args:
            allTasksDone is a deferred that will get fired once all the tasks
            have been completed.
        """
        self.doneTasks = 0
        self.tasks = 0

        self.completedScheduling = False

        self.allTasksDone = allTasksDone

    def created(self):
        self.tasks += 1

    def taskDone(self, result):
        self.doneTasks += 1
        if self.completedScheduling and \
                self.doneTasks == self.tasks:
            self.allTasksDone.callback(None)

    def allTasksScheduled(self):
        self.completedScheduling = True



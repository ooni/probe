import time

from twisted.internet import defer, reactor

from ooni import errors as e
from ooni.settings import config
from ooni import otime


class BaseTask(object):
    _timer = None

    _running = None

    def __init__(self):
        """
        If you want to schedule a task multiple times, remember to create fresh
        instances of it.
        """
        self.failures = 0

        self.startTime = time.time()
        self.runtime = 0

        # This is a deferred that gets called when a test has reached it's
        # final status, this means: all retries have been attempted or the test
        # has successfully executed.
        # Such deferred will be called on completion by the TaskManager.
        self.done = defer.Deferred()

    def _failed(self, failure):
        self.failures += 1
        self.failed(failure)
        return failure

    def _succeeded(self, result):
        self.runtime = time.time() - self.startTime
        self.succeeded(result)
        return result

    def start(self):
        self._running = defer.maybeDeferred(self.run)
        self._running.addErrback(self._failed)
        self._running.addCallback(self._succeeded)
        return self._running

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


class TaskWithTimeout(BaseTask):
    timeout = 30
    # So that we can test the callLater calls
    clock = reactor

    def _timedOut(self):
        """Internal method for handling timeout failure"""
        if self._running:
            self._failed(e.TaskTimedOut)
            self._running.cancel()

    def _cancelTimer(self):
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


class Measurement(TaskWithTimeout):
    def __init__(self, test_instance, test_method, test_input):
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
        self.testInstance = test_instance
        self.testInstance.input = test_input

        self.testInstance.setUp()
        if 'input' not in self.testInstance.report.keys():
            self.testInstance.report['input'] = self.testInstance.input

        self.netTestMethod = getattr(self.testInstance, test_method)

        if 'timeout' in dir(test_instance):
            if isinstance(test_instance.timeout, int) or isinstance(test_instance.timeout, float):
                # If the test has a timeout option set we set the measurement
                # timeout to that value + 8 seconds to give it enough time to
                # trigger it's internal timeout before we start trigger the
                # measurement timeout.
                self.timeout = test_instance.timeout + 8
        elif config.advanced.measurement_timeout:
            self.timeout = config.advanced.measurement_timeout
        TaskWithTimeout.__init__(self)

    def succeeded(self, result):
        pass

    def failed(self, failure):
        pass

    def run(self):
        if 'measurement_start_time' not in self.testInstance.report.keys():
            self.testInstance.report['measurement_start_time'] = otime.timestampNowLongUTC()
        if not hasattr(self.testInstance, '_start_time'):
            self.testInstance._start_time = time.time()
        return self.netTestMethod()


class ReportEntry(TaskWithTimeout):
    def __init__(self, reporter, entry):
        self.reporter = reporter
        self.entry = entry

        if config.advanced.reporting_timeout:
            self.timeout = config.advanced.reporting_timeout
        TaskWithTimeout.__init__(self)

    def run(self):
        return self.reporter.writeReportEntry(self.entry)

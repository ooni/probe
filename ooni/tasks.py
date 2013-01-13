import time

from twisted.internet import defer, reactor

class BaseTask(object):
    _timer = None

    def __init__(self):
        self.running = False
        self.failures = 0

        self.startTime = time.time()
        self.runtime = 0

        # This is a deferred that gets called when a test has reached it's
        # final status, this means: all retries have been attempted or the test
        # has successfully executed.
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
    def __init__(self, test_class, test_method, test_input, net_test):
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

    def succeeded(self):
        self.net_test.succeeded(self)

    def failed(self):
        pass

    def timedOut(self):
        self.net_test.timedOut()

    def run(self):
        return defer.maybeDeferred(self.test)

class ReportEntry(TaskWithTimeout):
    def __init__(self, reporter, measurement):
        self.reporter = reporter
        self.measurement = measurement
        TaskWithTimeout.__init__(self)

    def run(self):
        return self.reporter.writeReportEntry(self.measurement)


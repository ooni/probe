class BaseTask(object):
    _timer = None

    def __init__(self):
        self.running = False
        self.failures = 0

    def _failed(self, failure):
        self.failures += 1
        self.failed(failure)
        return

    def _run(self):
        d = self.run()
        d.addErrback(self._failed)
        d.addCallback(self._succeeded)
        return d

    def _succeeded(self, result):
        self.succeeded(result)

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

    def _timedOut(self):
        """Internal method for handling timeout failure"""
        self.timedOut()

    def _cancelTimer(self):
        if self._timer:
            self._timer.cancel()

    def _succeeded(self, result):
        self._cancelTimer()
        BaseTask._succeeded(self, result)

    def _failed(self, failure):
        self._cancelTimer()
        BaseTask._failed(self, failure)

    def _run(self):
        d = BaseTask._run(self)
        self._timer = reactor.callLater(self.timeout, self._timedOut)
        return d

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
        self.net_test.succeeded()

    def failed(self):
        pass

    def timedOut(self):
        self.net_test.timedOut()

    def run(self):
        d = defer.maybeDeferred(self.test)
        d.addCallback(self.success)
        d.addErrback(self.failure)
        return d

class ReportEntry(TimedOutTask):
    def __init__(self, reporter, measurement):
        self.reporter = reporter
        self.measurement = measurement
        TimedOutTask.__init__(self)

    def run(self):
        return self.reporter.writeReportEntry(self.measurement)


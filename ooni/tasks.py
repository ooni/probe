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



from ooni.tasks import BaseTask, TaskWithTimeout
from twisted.python import failure
from ooni.nettest import NetTest
from ooni.managers import TaskManager
from twisted.internet import defer

class MockMeasurementFailOnce(BaseTask):
    def run(self):
        f = open('dummyTaskFailOnce.txt', 'w')
        f.write('fail')
        f.close()
        if self.failure >= 1:
            return defer.succeed()
        else:
            return defer.fail()

class MockMeasurementManager(TaskManager):
    def __init__(self):
        self.successes = []

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))

class MockReporter(object):
    def write(self, measurement):
        pass

## from test_managers
mockFailure = failure.Failure(Exception('mock'))

class MockSuccessTask(BaseTask):
    def run(self):
        return defer.succeed(42)

class MockFailTask(BaseTask):
    def run(self):
        return defer.fail(mockFailure)

class MockFailOnceTask(BaseTask):
    def run(self):
        if self.failures >= 1:
            return defer.succeed(42)
        else:
            return defer.fail(mockFailure)

class MockSuccessTaskWithTimeout(TaskWithTimeout):
    def run(self):
        return defer.succeed(42)

class MockFailTaskThatTimesOut(TaskWithTimeout):
    def run(self):
        return defer.Deferred()

class MockTimeoutOnceTask(TaskWithTimeout):
    def run(self):
        if self.failures >= 1:
            return defer.succeed(42)
        else:
            return defer.Deferred()

class MockFailTaskWithTimeout(TaskWithTimeout):
    def run(self):
        return defer.fail(mockFailure)

class MockTaskManager(TaskManager):
    def __init__(self):
        self.successes = []

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))

class MockNetTest(object):
    def __init__(self):
        self.successes = []

    def succeeded(self, measurement):
        self.successes.append(measurement)

class MockMeasurement(TaskWithTimeout):
    def __init__(self, net_test):
        TaskWithTimeout.__init__(self)
        self.netTest = net_test

    def succeeded(self, result):
        return self.netTest.succeeded(self)

class MockSuccessMeasurement(MockMeasurement):
    def run(self):
        return defer.succeed(42)

class MockFailMeasurement(MockMeasurement):
    def run(self):
        return defer.fail(mockFailure)

class MockFailOnceMeasurement(MockMeasurement):
    def run(self):
        if self.failures >= 1:
            return defer.succeed(42)
        else:
            return defer.fail(mockFailure)

class MockDirector(object):
    def __init__(self):
        self.successes = []

    def measurementFailed(self, failure, measurement):
        pass

    def measurementSucceeded(self, measurement):
        self.successes.append(measurement)

## from test_reporter.py
class MockOReporter(object):
    def __init__(self):
        self.created = defer.Deferred()

    def writeReportEntry(self, entry):
        pass

    def finish(self):
        pass

    def createReport(self):
        pass


class MockTaskManager(TaskManager):
    def __init__(self):
        self.successes = []

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))

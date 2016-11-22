from twisted.python import failure
from twisted.internet import defer

from ooni.tasks import BaseTask, TaskWithTimeout
from ooni.managers import TaskManager
from ooni.backend_client import CollectorClient

class MockMeasurementFailOnce(BaseTask):
    def run(self):
        f = open('dummyTaskFailOnce.txt', 'w')
        f.write('fail')
        f.close()
        if self.failure >= 1:
            return defer.succeed(self)
        else:
            return defer.fail(failure.Failure)


class MockMeasurementManager(TaskManager):
    def __init__(self):
        self.successes = []
        TaskManager.__init__(self)

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))


class MockReporter(object):
    def __init__(self):
        self.created = defer.Deferred()

    def writeReportEntry(self, entry):
        pass

    def createReport(self):
        self.created.callback(self)

    def finish(self):
        pass


class MockFailure(Exception):
    pass

# # from test_managers
mockFailure = failure.Failure(MockFailure('mock'))


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
        return self.netTest.succeeded(42)


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
        return defer.succeed(42)

    def finish(self):
        pass

    def createReport(self):
        from ooni.utils import log

        log.debug("Creating report with %s" % self)
        self.created.callback(self)


class MockOReporterThatFailsWrite(MockOReporter):
    def writeReportEntry(self, entry):
        raise MockFailure


class MockOReporterThatFailsOpen(MockOReporter):
    def createReport(self):
        raise MockFailure


class MockOReporterThatFailsWriteOnce(MockOReporter):
    def __init__(self):
        self.failure = 0
        MockOReporter.__init__(self)

    def writeReportEntry(self, entry):
        if self.failure >= 1:
            return defer.succeed(42)
        else:
            self.failure += 1
            raise MockFailure


class MockTaskManager(TaskManager):
    def __init__(self):
        self.successes = []
        TaskManager.__init__(self)

    def failed(self, failure, task):
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))


class MockBouncerClient(object):
    def __init__(self, *args, **kw):
        self.backend_type = "onion"

    def lookupTestHelpers(self, required_test_helpers):
        ret = {
            'default': {
                'address': '127.0.0.1',
                'collector': 'httpo://thirteenchars123.onion'
            }
        }
        for required_test_helper in required_test_helpers:
            ret[required_test_helper] = {
                'address': '127.0.0.1',
                'collector': 'httpo://thirteenchars123.onion'
            }
        return defer.succeed(ret)

    def lookupTestCollector(self, net_tests):
        ret = {
            'net-tests': [
            ]
        }
        for net_test in net_tests:
            test_helpers ={}
            for test_helper in net_test['test-helpers']:
                test_helpers[test_helper] = '127.0.0.1'

            ret['net-tests'].append({
                'name': net_test['name'],
                'version': net_test['version'],
                'input-hashes': net_test['input-hashes'],
                'collector': 'httpo://thirteenchars123.onion',
                'collector-alternate': [
                    {'type': 'https', 'address': 'https://collector.ooni.io'},
                    {'type': 'http', 'address': 'http://collector.ooni.io'},
                    {
                        'type': 'cloudfront',
                        'address': 'https://address.cloudfront.net',
                        'front': 'front.cloudfront.net'
                    },
                ],
                'test-helpers': test_helpers
            })
        return defer.succeed(ret)


class MockCollectorClient(CollectorClient):
    def isSupported(self):
        return True

    def isReachable(self):
        return defer.succeed(True)

from ooni.tasks import BaseTask
from ooni.nettest import NetTest
from ooni.managers import TaskManager

class MockMeasurement(BaseTask):
    def run(self):
        f = open('foo.txt', 'w')
        f.write('testing')
        f.close()

        return defer.succeed(self)

class MockMeasurementFailOnce(BaseTask):
    def run(self):
        f = open('dummyTaskFailOnce.txt', 'w')
        f.write('fail')
        f.close()
        if self.failure >= 1:
            return defer.succeed()
        else:
            return defer.fail()

class MockNetTest(NetTest):
    def __init__(self, num_measurements=1):
        NetTest.__init__(self, StringIO(net_test_string), dummyOptions)
        self.num_measurements = num_measurements
    def generateMeasurements(self):
        for i in range(self.num_measurements):
            yield MockMeasurement()

class MockDirector(object):
    def __init__(self):
        pass

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



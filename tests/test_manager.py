from ooni.measurements import Measurement, NetTest
from ooni.managers import Director, MeasurementsManager
from ooni.tasks import BaseTask, TaskWithTimeout
from os import unlink
from StringIO import StringIO
from tempfile import TemporaryFile, mkstemp
from twisted.trial import unittest
from twisted.internet import defer, reactor

net_test_string = """
from twisted.python import usage
from ooni.nettest import NetTestCase

class UsageOptions(usage.Options):
    optParameters = [['spam', 's', 'ham']]

class DummyTestCase(NetTestCase):
    usageOptions = UsageOptions

    def test_a(self):
        self.report['bar'] = 'bar'

    def test_b(self):
        self.report['foo'] = 'foo'
"""

dummyInputs = range(1)
dummyOptions = {'spam': 'notham'}

#dummyNetTest = NetTest(net_test_file, inputs, options)

class DummyMeasurement(BaseTask):
    def run(self):
        f = open('foo.txt', 'w')
        f.write('testing')
        f.close()

        return defer.succeed(self)

class DummyMeasurementFailOnce(BaseTask):
    def run(self):
        f = open('dummyTaskFailOnce.txt', 'w')
        f.write('fail')
        f.close()
        if self.failure >= 1:
            return defer.succeed()
        else:
            return defer.fail()

class DummyNetTest(NetTest):
    def __init__(self, num_measurements=1):
        NetTest.__init__(self, StringIO(net_test_string), dummyInputs, dummyOptions)
        self.num_measurements = num_measurements
    def generateMeasurements(self):
        for i in range(self.num_measurements):
            yield DummyMeasurement()

class DummyDirector(object):
    def __init__(self):
        pass

class DummyReporter(object):
    def __init__(self):
        pass
    def write(self, result):
        pass

class TestNetTest(unittest.TestCase):
    def test_load_net_test_from_file(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        __, net_test_file = mkstemp()
        with open(net_test_file, 'w') as f:
            f.write(net_test_string)
        f.close()

        net_test_from_string = NetTest(StringIO(net_test_string),
                dummyInputs, dummyOptions, DummyReporter())
        net_test_from_file = NetTest(net_test_file, dummyInputs,
                dummyOptions, DummyReporter())

        # XXX: the returned classes are not the same because the
        # module path is not correct, so the test below fails.
        # TODO: figure out how to verify that the instantiated
        # classes are done so properly.

        #self.assertEqual(net_test_from_string.test_cases,
        #        net_test_from_file.test_cases)
        unlink(net_test_file)

class TestMeasurementsManager(unittest.TestCase):
    def setUp(self):
        self.mock_mm = MeasurementsManager()
        self.mock_mm.director = DummyDirector()

    def test_schedule_measurement(self):
        # testing schedule()
        # run a single measurement
        measurement = DummyMeasurement()
        self.mock_mm.concurrency = 1
        self.mock_mm.start()
        self.mock_mm.schedule(measurement)
        d = self.mock_mm.run(measurement)
        def f(x):
            self.assertEqual(self.mock_mm.completedMeasurements, 1)
        d.addCallback(f)
        return d

    def test_all_slots_full(self):
        """
        Test case where active_measurements is full
        """
        self.mock_mm.concurrency = 1
        self.mock_mm.start()

        dl = []
        for x in xrange(2):
            measurement = DummyMeasurement()
            dl.append(self.mock_mm.schedule(measurement))

        def f(z): print self.mock_mm.completedMeasurements

        assert dl is not None
        d = defer.DeferredList(dl)
        assert d is not None
        d.addCallback(f)
        return d

    def test_populate_active_measurements(self):
        """
        Test that populates the full set of active measurements
        """
        pass

    def test_fail_and_reschedule(self):
        """docstring for test_fail_and_reschedule"""
        pass

    def test_fail_timeout_and_reschedule(self):
        pass

    def test_all_completed(self):
        """
        all inputs have been consumed and all tests have a final status.
        """
        pass

    def test_measurements_exhausted(self):
        """
        inputs consumed, but still have running measurements
        """
        pass

class TestDirector(unittest.TestCase):
    def setUp(self):
        self.director = Director()

    def test_successful_measurement(self):
        pass

    def test_failing_measurment(self):
        pass

    def test_retry_twice_measurement(self):
        pass

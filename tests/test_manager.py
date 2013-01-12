from StringIO import StringIO
from twisted.trial import unittest

from ooni.manager import Measurement, Measurements
from ooni.manager import NetTest, OManager
from ooni.manager import BaseTask, TaskWithTimeout

net_test_file = StringIO()
net_test_file.write("""
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
""")

dummyInputs = range(10)
dummyOptions = {'spam': 'notham'}

#dummyNetTest = NetTest(net_test_file, inputs, options)

class DummyMeasurement(BaseTask):
    def run(self):
        f = open('foo.txt', 'w')
        f.write('testing')
        f.close()

        return defer.succeed()

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
    def generateMeasurements(self):
        for i in range(10):
            yield DummyTask()

class DummyManager(object):
    def __init__(self):
        pass

class TestNetTest(unittest.TestCase):
    def test_load_net_test_from_file(self):
        """
        Given a file like object verify that the net test cases are properly
        generated.
        """
        net_test = NetTest(net_test_file, dummyInputs, dummyOptions)
        self.assertEqual([(DummyTestCase, 'test_a'), (DummyTestCase,
            'test_b')], net_test.test_cases)

    def test_net_test_timeout(self):
        """Instantiate a test and verify that the timeout works properly when we call it."""
        net_test = NetTest(net_test_file, dummyInputs, dummyOptions)
        # Where net_test_file is a test that will take longer than 

class TestMeasurementsTracker(unittest.TestCase):
    def setUp(self):
        self.mock_mt = MeasurementsTracker(DummyManager())
        self.mock_mt.netTests = [DummyNetTest()]
        self.mock_mt.start()

    def test_schedule_measurement(self):
        # testing schedule()
        # run a single measurement
        measurement = DummyMeasurement()
        self.mock_mt.schedule(measurement)

    def test_all_slots_full(self):
        """
        Test case where active_measurements is full
        """
        pass

    def test_populate_active_measurements(self):
        """
        Test that populates the full set of active measurements
        """
        pass

    def test_fail_and_reschedule(self):
        """docstring for test_fail_and_reschedule"""
        pass

    def test_fail_timeout_and_reschedule():
        pass

    def test_all_completed(self):
        """
        all inputs have been consumed and all tests have a final status.
        """
        pass

    def test_measurements_exhausted():
        """
        inputs consumed, but still have running measurements
        """
        pass



class TestManager(unittest.TestCase):
    def setUp(self):
        self.manager = OManager

    def test_successful_measurement(self):
        pass

    def test_failing_measurment(self):
        pass

    def test_retry_twice_measurement(self):
        pass



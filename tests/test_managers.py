from twisted.trial import unittest
from twisted.python import failure
from twisted.internet import defer, task

from ooni.tasks import BaseTask, TaskWithTimeout
from ooni.managers import TaskManager, MeasurementManager

from tests.mocks import MockSuccessTask, MockFailTask, MockFailOnceTask
from tests.mocks import MockSuccessTaskWithTimeout, MockFailTaskThatTimesOut
from tests.mocks import MockTimeoutOnceTask, MockFailTaskWithTimeout
from tests.mocks import MockTaskManager, mockFailure, MockDirector
from tests.mocks import MockNetTest, MockMeasurement, MockSuccessMeasurement
from tests.mocks import MockFailMeasurement, MockFailOnceMeasurement

class TestTaskManager(unittest.TestCase):
    timeout = 1
    def setUp(self):
        self.measurementManager = MockTaskManager()
        self.measurementManager.concurrency = 10
        self.measurementManager.retries = 2

        self.measurementManager.start()

        self.clock = task.Clock()

    def schedule_successful_tasks(self, task_type, number=1):
        all_done = []
        for x in range(number):
            mock_task = task_type()
            all_done.append(mock_task.done)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            for task_result, task_instance in self.measurementManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, task_type)

        return d

    def schedule_failing_tasks(self, task_type, number=1):
        all_done = []
        for x in range(number):
            mock_task = task_type()
            all_done.append(mock_task.done)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            # 10*2 because 2 is the number of retries
            self.assertEqual(len(self.measurementManager.failures), number*3)
            for task_result, task_instance in self.measurementManager.failures:
                self.assertEqual(task_result, mockFailure)
                self.assertIsInstance(task_instance, task_type)

        return d

    def test_schedule_successful_one_task(self):
        return self.schedule_successful_tasks(MockSuccessTask)

    def test_schedule_successful_one_task_with_timeout(self):
        return self.schedule_successful_tasks(MockSuccessTaskWithTimeout)

    def test_schedule_failing_tasks_that_timesout(self):
        self.measurementManager.retries = 0

        task_type = MockFailTaskThatTimesOut
        task_timeout = 5

        mock_task = task_type()
        mock_task.timeout = task_timeout
        mock_task.clock = self.clock

        self.measurementManager.schedule(mock_task)

        self.clock.advance(task_timeout)

        @mock_task.done.addBoth
        def done(res):
            self.assertEqual(len(self.measurementManager.failures), 1)
            for task_result, task_instance in self.measurementManager.failures:
                self.assertIsInstance(task_instance, task_type)

        return mock_task.done

    def test_schedule_time_out_once(self):
        task_type = MockTimeoutOnceTask
        task_timeout = 5

        mock_task = task_type()
        mock_task.timeout = task_timeout
        mock_task.clock = self.clock

        self.measurementManager.schedule(mock_task)

        self.clock.advance(task_timeout)

        @mock_task.done.addBoth
        def done(res):
            self.assertEqual(len(self.measurementManager.failures), 1)
            for task_result, task_instance in self.measurementManager.failures:
                self.assertIsInstance(task_instance, task_type)

            for task_result, task_instance in self.measurementManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, task_type)

        return mock_task.done


    def test_schedule_failing_one_task(self):
        return self.schedule_failing_tasks(MockFailTask)

    def test_schedule_failing_one_task_with_timeout(self):
        return self.schedule_failing_tasks(MockFailTaskWithTimeout)

    def test_schedule_successful_ten_tasks(self):
        return self.schedule_successful_tasks(MockSuccessTask, number=10)

    def test_schedule_failing_ten_tasks(self):
        return self.schedule_failing_tasks(MockFailTask, number=10)

    def test_schedule_successful_27_tasks(self):
        return self.schedule_successful_tasks(MockSuccessTask, number=27)

    def test_schedule_failing_27_tasks(self):
        return self.schedule_failing_tasks(MockFailTask, number=27)

    def test_task_retry_and_succeed(self):
        mock_task = MockFailOnceTask()
        self.measurementManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(res):
            self.assertEqual(len(self.measurementManager.failures), 1)

            self.assertEqual(self.measurementManager.failures,
                    [(mockFailure, mock_task)])
            self.assertEqual(self.measurementManager.successes,
                    [(42, mock_task)])

        return mock_task.done

    def test_task_retry_and_succeed_56_tasks(self):
        all_done = []
        for x in range(56):
            mock_task = MockFailOnceTask()
            all_done.append(mock_task.done)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            self.assertEqual(len(self.measurementManager.failures), 56)

            for task_result, task_instance in self.measurementManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, MockFailOnceTask)

        return d

class TestMeasurementManager(unittest.TestCase):
    def setUp(self):
        mock_director = MockDirector()

        self.measurementManager = MeasurementManager()
        self.measurementManager.director = mock_director

        self.measurementManager.concurrency = 10
        self.measurementManager.retries = 2

        self.measurementManager.start()

        self.mockNetTest = MockNetTest()

    def test_schedule_and_net_test_notified(self, number=1):
        # XXX we should probably be inheriting from the base test class
        mock_task = MockSuccessMeasurement(self.mockNetTest)
        self.measurementManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(res):
            self.assertEqual(self.mockNetTest.successes,
                    [mock_task])

            self.assertEqual(len(self.mockNetTest.successes), 1)
        return mock_task.done

    def test_schedule_failing_one_measurement(self):
        mock_task = MockFailMeasurement(self.mockNetTest)
        self.measurementManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(failure):
            self.assertEqual(len(self.measurementManager.failures), 3)

            self.assertEqual(failure, (mockFailure, mock_task))
            self.assertEqual(len(self.mockNetTest.successes), 0)

        return mock_task.done



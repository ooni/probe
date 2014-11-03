import os

from twisted.trial import unittest
from twisted.internet import defer, task

from ooni.managers import MeasurementManager

from ooni.tests.mocks import MockSuccessTask, MockFailTask, MockFailOnceTask, MockFailure
from ooni.tests.mocks import MockSuccessTaskWithTimeout, MockFailTaskThatTimesOut
from ooni.tests.mocks import MockTimeoutOnceTask, MockFailTaskWithTimeout
from ooni.tests.mocks import MockTaskManager, mockFailure, MockDirector
from ooni.tests.mocks import MockNetTest, MockSuccessMeasurement
from ooni.tests.mocks import MockFailMeasurement
from ooni.settings import config


class TestTaskManager(unittest.TestCase):
    timeout = 1

    def setUp(self):
        self.measurementManager = MockTaskManager()
        self.measurementManager.concurrency = 20
        self.measurementManager.retries = 2

        self.measurementManager.start()

        self.clock = task.Clock()
        data_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(data_dir, '..', '..', 'data')
        self.old_datadir = ""
        if hasattr(config.global_options, 'datadir'):
            self.old_datadir = config.global_options['datadir']
        config.global_options['datadir'] = data_dir
        config.set_paths()

    def tearDown(self):
        if self.old_datadir == "":
            del config.global_options['datadir']
        else:
            config.global_options['datadir'] = self.old_datadir
        config.set_paths()

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
            mock_task.done.addErrback(lambda x: None)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)

        @d.addCallback
        def done(res):
            # 10*2 because 2 is the number of retries
            self.assertEqual(self.measurementManager.failures, number * 3)
            # XXX @aagbsn is there a reason why you switched to using an int
            # over a using a list?
            # self.assertEqual(len(self.measurementManager.failures), number*3)
            # for task_result, task_instance in self.measurementManager.failures:
            # self.assertEqual(task_result, mockFailure)
            # self.assertIsInstance(task_instance, task_type)

        return d

    def test_schedule_failing_with_mock_failure_task(self):
        mock_task = MockFailTask()
        self.measurementManager.schedule(mock_task)
        self.assertFailure(mock_task.done, MockFailure)
        return mock_task.done

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
            self.assertEqual(self.measurementManager.failures, 1)
            # self.assertEqual(len(self.measurementManager.failures), 1)
            # for task_result, task_instance in self.measurementManager.failures:
            # self.assertIsInstance(task_instance, task_type)

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
            self.assertEqual(self.measurementManager.failures, 1)
            # self.assertEqual(len(self.measurementManager.failures), 1)
            # for task_result, task_instance in self.measurementManager.failures:
            # self.assertIsInstance(task_instance, task_type)

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
            self.assertEqual(self.measurementManager.failures, 1)
            # self.assertEqual(len(self.measurementManager.failures), 1)
            # self.assertEqual(self.measurementManager.failures,
            # [(mockFailure, mock_task)])
            self.assertEqual(self.measurementManager.successes,
                             [(42, mock_task)])

        return mock_task.done

    def test_task_retry_and_succeed_56_tasks(self):
        """
        XXX this test fails in a non-deterministic manner.
        """
        all_done = []
        number = 56
        for x in range(number):
            mock_task = MockFailOnceTask()
            all_done.append(mock_task.done)
            self.measurementManager.schedule(mock_task)

        d = defer.DeferredList(all_done)

        @d.addCallback
        def done(res):
            self.assertEqual(self.measurementManager.failures, number)
            # self.assertEqual(len(self.measurementManager.failures), number)
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
                             [42])

            self.assertEqual(len(self.mockNetTest.successes), 1)

        return mock_task.done

    def test_schedule_failing_one_measurement(self):
        mock_task = MockFailMeasurement(self.mockNetTest)
        self.measurementManager.schedule(mock_task)

        @mock_task.done.addErrback
        def done(failure):
            self.assertEqual(self.measurementManager.failures, 3)
            # self.assertEqual(len(self.measurementManager.failures), 3)

            self.assertEqual(failure, mockFailure)
            self.assertEqual(len(self.mockNetTest.successes), 0)

        return mock_task.done

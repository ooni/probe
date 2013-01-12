from twisted.trial import unittest
from twisted.python import failure
from twisted.internet import defer

from ooni.tasks import BaseTask, TaskWithTimeout
from ooni.managers import TaskManager, MeasurementManager

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

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.measurementManager = MockTaskManager()
        self.measurementManager.concurrency = 10
        self.measurementManager.retries = 2

        self.measurementManager.start()

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

    def test_schedule_successful_one_task(self):
        return self.schedule_successful_tasks(MockSuccessTask)

    def test_schedule_successful_one_task_with_timeout(self):
        return self.schedule_successful_tasks(MockSuccessTaskWithTimeout)

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
            self.taskManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            self.assertEqual(len(self.taskManager.failures), 56)

            for task_result, task_instance in self.taskManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, MockFailOnceTask)

        return d


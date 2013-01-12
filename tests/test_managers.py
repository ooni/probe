from twisted.trial import unittest
from twisted.python import failure
from twisted.internet import defer

from ooni.tasks import BaseTask
from ooni.managers import TaskManager


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

class MockTaskManager(TaskManager):
    def __init__(self):
        self.successes = []

    def failed(self, failure, task):
        # print "TASK"
        # print task
        # print "FAILURES (%s)" % task.failures
        # print failure
        pass

    def succeeded(self, result, task):
        self.successes.append((result, task))

class TestTaskManager(unittest.TestCase):
    def setUp(self):
        self.taskManager = MockTaskManager()
        self.taskManager.concurrency = 10
        self.taskManager.retries = 2

        self.taskManager.start()

    def tearDown(self):
        pass

    def test_schedule_successful_one_task(self):
        mock_task = MockSuccessTask()
        self.taskManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(res):
            self.assertEqual(self.taskManager.successes,
                    [(42, mock_task)])
        return mock_task.done

    def test_schedule_failing_one_task(self):
        mock_task = MockFailTask()
        self.taskManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(failure):
            self.assertEqual(len(self.taskManager.failures), 3)

            self.assertEqual(failure, (mockFailure, mock_task))

        return mock_task.done

    def test_schedule_successful_ten_tasks(self):
        all_done = []
        for x in range(10):
            mock_task = MockSuccessTask()
            all_done.append(mock_task.done)
            self.taskManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            for task_result, task_instance in self.taskManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, MockSuccessTask)

        return d

    def test_schedule_failing_ten_tasks(self):
        all_done = []
        for x in range(10):
            mock_task = MockFailTask()
            all_done.append(mock_task.done)
            self.taskManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            # 10*2 because 2 is the number of retries
            self.assertEqual(len(self.taskManager.failures), 10*3)
            for task_result, task_instance in self.taskManager.failures:
                self.assertEqual(task_result, mockFailure)
                self.assertIsInstance(task_instance, MockFailTask)

        return d

    def test_schedule_successful_27_tasks(self):
        all_done = []
        for x in range(27):
            mock_task = MockSuccessTask()
            all_done.append(mock_task.done)
            self.taskManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            for task_result, task_instance in self.taskManager.successes:
                self.assertEqual(task_result, 42)
                self.assertIsInstance(task_instance, MockSuccessTask)

        return d

    def test_schedule_failing_27_tasks(self):
        all_done = []
        for x in range(27):
            mock_task = MockFailTask()
            all_done.append(mock_task.done)
            self.taskManager.schedule(mock_task)

        d = defer.DeferredList(all_done)
        @d.addCallback
        def done(res):
            # 10*2 because 2 is the number of retries
            self.assertEqual(len(self.taskManager.failures), 27*3)
            for task_result, task_instance in self.taskManager.failures:
                self.assertEqual(task_result, mockFailure)
                self.assertIsInstance(task_instance, MockFailTask)

        return d


    def test_task_retry_and_succeed(self):
        mock_task = MockFailOnceTask()
        self.taskManager.schedule(mock_task)

        @mock_task.done.addCallback
        def done(res):
            self.assertEqual(len(self.taskManager.failures), 1)

            self.assertEqual(self.taskManager.failures,
                    [(mockFailure, mock_task)])
            self.assertEqual(self.taskManager.successes,
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


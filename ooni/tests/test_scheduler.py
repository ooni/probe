import os
import sys
import shutil
import random
import tempfile

from twisted.internet import reactor, task, defer
from twisted.trial import unittest

from ooni.agent.scheduler import ScheduledTask, DidNotRun, FileSystemlockAndMutex

class TestScheduler(unittest.TestCase):
    def test_scheduled_task(self):
        schedule = "@daily"
        identifier = "dummy"
        scheduler_directory = tempfile.mkdtemp()
        scheduled_task = ScheduledTask(schedule=schedule,
                                       identifier=identifier,
                                       scheduler_directory=scheduler_directory
        )
        self.assertEqual(scheduled_task.should_run, True)
        self.assertFailure(scheduled_task.run(), NotImplementedError)
        self.assertEqual(scheduled_task.should_run, True)
        self.assertFalse(os.path.islink(os.path.join(scheduler_directory, identifier + '.lock')))
        shutil.rmtree(scheduler_directory)

    @defer.inlineCallbacks
    def test_call_twice_scheduled_task(self):
        """
        If we call the scheduled task twice in a row the second time it will not run.
        Tests for possible race conditions.
        """
        scheduler_directory = tempfile.mkdtemp()
        spam_path = os.path.join(scheduler_directory, 'spam.txt')
        class DummyST(ScheduledTask):
            def task(subself):
                self.assertTrue(os.path.islink(os.path.join(scheduler_directory, subself.identifier + '.lock')))
                with open(spam_path, 'a') as out_file:
                    out_file.write("I ran\n")

        schedule = "@daily"
        identifier = "dummy"
        dummy_st = DummyST(schedule=schedule,
                           identifier=identifier,
                           scheduler_directory=scheduler_directory
        )

        dummy_st.run()
        yield self.assertFailure(dummy_st.run(), DidNotRun)

        with open(spam_path) as in_file:
            self.assertEqual(len(in_file.readlines()), 1)

        self.assertEqual(dummy_st.should_run, False)
        self.assertFalse(os.path.islink(os.path.join(scheduler_directory, identifier + '.lock')))
        shutil.rmtree(scheduler_directory)

    def test_thundering_herd(self):
        lockno = int(os.getenv('TTH_LOCKNO', str(sys.getrecursionlimit() + 16)))
        scheduler_directory = tempfile.mkdtemp()
        counter = os.path.join(scheduler_directory, 'counter')
        class DummyST(ScheduledTask):
            @defer.inlineCallbacks
            def task(subself):
                self.assertTrue(os.path.islink(os.path.join(scheduler_directory, subself.identifier + '.lock')))
                with open(counter, 'w+') as fd:
                    data = fd.read()
                    fd.seek(0)
                    if not data:
                        fd.write('1')
                        yield task.deferLater(reactor, 1, lambda: 42)
                    else:
                        self.assertTrue(False) # should be unreachable due to schedule
        identifier = "dummy"
        dummy_st = DummyST(schedule='@daily', identifier=identifier, scheduler_directory=scheduler_directory)
        dl = defer.DeferredList([dummy_st.run() for i in xrange(lockno)], consumeErrors=True)
        @dl.addBoth
        def so_what(results):
            self.assertFalse(os.path.islink(os.path.join(scheduler_directory, identifier + '.lock')))
            self.assertEqual(results[0], (True, None)) # do not expect to get `42` here
            for okflag, ex in results[1:]:
                self.assertEqual(okflag, False)
                ex.trap(DidNotRun)
            self.assertEqual(dummy_st.should_run, False)
            with open(counter, 'r') as fd:
                self.assertEqual(fd.read(), '1')
            shutil.rmtree(scheduler_directory)
        return dl

    @defer.inlineCallbacks
    def test_filesystem_lock_and_mutex(self):
        lock_dir = tempfile.mkdtemp()
        lock_path = os.path.join(lock_dir, 'lock')

        lock = FileSystemlockAndMutex(lock_path)

        os.symlink(str(2**30), lock_path) # that's non-existend PID for sure

        lock_count = 100
        unlock_count = 0
        dl = []
        for i in range(lock_count):
            dl.append(lock.acquire())
            if random.choice([0, 1]) == 0:
                unlock_count += 1
                lock.release()

        for i in range(lock_count - unlock_count):
            lock.release()

        yield defer.DeferredList(dl)
        self.assertFalse(lock.locked)

        shutil.rmtree(lock_dir)

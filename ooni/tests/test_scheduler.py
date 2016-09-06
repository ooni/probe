import os
import shutil
import tempfile

from twisted.internet import defer
from twisted.trial import unittest

from ooni.agent.scheduler import ScheduledTask, DidNotRun

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
            def task(self):
                with open(spam_path, 'w') as out_file:
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
        shutil.rmtree(scheduler_directory)

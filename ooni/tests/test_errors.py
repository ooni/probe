from twisted.trial import unittest

import ooni.errors

class TestErrors(unittest.TestCase):

    def test_catch_child_failures_before_parent_failures(self):
        """
        Verify that more specific Failures are caught first by
        handleAllFailures() and failureToString().

        Fails if a subclass is listed after its parent Failure.
        """

        # Check each Failure against all subsequent failures
        for index, (failure, _) in enumerate(ooni.errors.known_failures):
            for sub_failure, _ in ooni.errors.known_failures[index+1:]:

                # Fail if subsequent Failure inherits from the current Failure
                self.assertNotIsInstance(sub_failure(None), failure)

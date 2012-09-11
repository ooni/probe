from twisted.trial import reporter

class TestResult(reporter.TestResult):
    """
    Accumulates the results of several ooni.nettest.TestCases.

    The output format of a TestResult is YAML and it will contain all the basic
    information that a test result should contain.
    """
    def __init__(self):
        super(TestResult, self).__init__()



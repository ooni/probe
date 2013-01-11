from .tasks import TaskWithTimeout

class NetTest(object):
    director = None

    def __init__(self, net_test_file, inputs, options, report):
        """
        net_test_file:
            is a file object containing the test to be run.

        inputs:
            is a generator containing the inputs to the net test.

        options:
            is a dict containing the opitions to be passed to the net test.
        """
        self.test_cases = self.loadNetTestFile(net_test_file)
        self.inputs = inputs
        self.options = options

    def loadNetTestFile(self, net_test_file):
        """
        Creates all the necessary test_cases (a list of tuples containing the
        NetTestCase (test_class, test_method))

        example:
            [(test_classA, test_method1),
            (test_classA, test_method2),
            (test_classA, test_method3),
            (test_classA, test_method4),
            (test_classA, test_method5),

            (test_classB, test_method1),
            (test_classB, test_method2)]

        Note: the inputs must be valid for test_classA and test_classB.

        net_test_file:
            is a file like object that will be used to generate the test_cases.
        """
        # XXX Not implemented
        raise NotImplemented

    def timedOut(self, measurement):
        """
        This gets called when a measurement has timed out. This may or may not
        trigger a retry inside of MeasurementsTracker.
        """
        self.director.measurementTimedOut(measurement)

    def failed(self, measurement, failure):
        """
        This gets called when a measurement has failed in the sense that all
        the retries have failed at successfully running the test.
        This means that it's a definitive failure and we will no longer make
        any attempts at re-running the measurement.
        """
        self.director.measurementFailed(measurement, failure)

    def succeeded(self, measurement):
        """
        This gets called when a measurement has failed.
        """
        self.report.write(measurement)

    def generateMeasurements(self):
        """
        This is a generator that yields measurements and sets their timeout
        value and their netTest attribute.
        """
        for test_input in self.inputs:
            for test_class, test_method in self.test_cases:
                measurement = Measurement(test_class, test_method, test_input)
                measurement.netTest = self
                measurement.timeout = self.rateLimiter.timeout
                yield measurement


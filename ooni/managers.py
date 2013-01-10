import itertools

from .ratelimiting import StaticRateLimiter
from .measurements import Measurement, NetTest

class MeasurementsManager(object):
    """
    This is the Measurement Tracker. In here we keep track of active measurements
    and issue new measurements once the active ones have been completed.

    MeasurementTracker does not keep track of the typology of measurements that
    it is running. It just considers a measurement something that has an input
    and a method to be called.

    NetTest on the contrary is aware of the typology of measurements that it is
    dispatching as they are logically grouped by test file.
    """
    retries = 2

    failures = []
    concurrency = 10

    _measurements = iter()
    _active_measurements = []

    def __init__(self, manager, netTests=None):
        self.netTests = netTests if netTests else []
        self.manager = manager

    @property
    def failedMeasurements(self):
        return len(self.failures)

    def start(self):
        """
        Start running the measurements.
        """
        self.populateMeasurements()
        self.runMoreMeasurements()

    def populateMeasurements(self):
        """
        Take all the setup netTests and create the measurements iterator from
        them.
        """
        for net_test in self.netTests:
            self._measurements = itertools.chain(self._measurements,
                    net_test.generateMeasurements())

    def availableSlots(self):
        """
        Returns the number of available slots for running tests.
        """
        return self.concurrency - len(self._active_measurements)

    def schedule(self, measurement):
        self._active_measurements.append(measurement)

        d = measurement.run()
        d.addCallback(self.done)
        d.addCallback(self.failed)
        return d

    def fillSlots(self):
        """
        Called on test completion and schedules measurements to be run for the
        available slots.
        """
        for _ in range(self.availableSlots()):
            try:
                measurement = self._measurements.next()
                self.schedule(measurement)
            except StopIteration:
                break

    def done(self, result, measurement):
        """
        We have successfully completed a measurement.
        """
        self._active_measurements.remove(measurement)
        self.completedMeasurements += 1

        self.fillSlots()

    def failed(self, failure, measurement):
        """
        The measurement has failed to complete.
        """
        self._active_measurements.remove(measurement)
        self.failures.append((failure, measurement))

        if measurement.failures < self.retries:
            self._measurements = itertools.chain(self._measurements,
                    iter(measurement))

        self.fillSlots()

class OManager(object):
    """
    Singleton object responsible for managing the Measurements Tracker and the
    Reporting Tracker.
    """

    _scheduledTests = 0

    def __init__(self, reporters=[]):
        self.reporters = reporters

        self.netTests = []

        self.measurementsManager = MeasurementsManager(manager=self,
                netTests=self.netTests)
        self.measurementsManager.manager = self

        self.reportingManager

    def writeReport(self, measurement):
        """
        Write to all the configured reporters.
        """
        for reporter in self.reporters:
            reporter.write(measurement)

    def writeFailure(self, measurement, failure):
        pass

    def addNetTest(self, net_test):
        """
        This is called to add a NetTest to the list of running network tests.
        """
        self.netTests.append(net_test)


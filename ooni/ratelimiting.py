class RateLimiter(object):
    """
    The abstract class that imposes limits over how measurements are scheduled,
    how retries are handled and when we should be giving up on a certain
    measurement.
    """
    @property
    def timeout(self):
        """
        After what timeout a certain test should be considered to have failed
        and attempt a retry if the maximum retry has not been reached.
        """
        raise NotImplemented

    @property
    def maxTimeout(self):
        """
        This is the maximum value that timeout can reach.
        """
        raise NotImplemented

    @property
    def concurrency(self):
        """
        How many concurrent requests should happen at the same time.
        """
        raise NotImplemented

    def timedOut(self, measurement):
        raise NotImplemented

    def completed(self, measurement):
        raise NotImplemented

    def failed(self, measurement):
        raise NotImplemented

class StaticRateLimiter(RateLimiter):
    """
    This is a static ratelimiter that returns constant values.
    """
    @property
    def timeout(self):
        return 10

    @property
    def maxTimeout(self):
        return 5 * 60

    @property
    def concurrency(self):
        return 10

    def timedOut(self, measurement):
        pass

    def completed(self, measurement):
        pass

    def failed(self, measurement, failure):
        pass

class TimeoutRateLimiter(RateLimiter):
    pass

class BandwidthRateLimiter(RateLimiter):
    pass


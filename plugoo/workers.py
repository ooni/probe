import gevent
from gevent.pool import Pool

class WorkFactory:
    """
    This class is responsible for producing
    units of work.
    """
    def __init__(self, assets=None,
                 nodes=None, rule=None):
        pass

    def _process_rule(self):
        pass

    def get_work_unit():
        pass

class UnitOfWork:
    def __init__(self, tests, poolsize=20,
                 unit_of_work=None):
        pass

    def _read_unit_of_work(self):
        pass

    def _build_pools(self):
        for i, x in enumerate(self.tests):
            if i % self.poolsize == 0:


    def do(self):
        with gevent.Timeout():
            self.pool.join()



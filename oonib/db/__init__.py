__all__ = ['createTables', 'database', 'transactor']

from twisted.python.threadpool import ThreadPool
from twisted.internet.defer import inlineCallbacks, returnValue, Deferred

from storm.locals import Store
from storm.uri import URI
from storm.databases.sqlite import SQLite

from oonib import database, transactor
from ooni.utils import log

@inlineCallbacks
def createTables():
    """
    XXX this is to be refactored and only exists for experimentation.
    """
    from oonib.db import models
    for model_name in models.__all__:
        try:
            model = getattr(m, model_name)
        except Exception, e:
            log.err("Error in db initting")
            log.err(e)
        try:
            log.debug("Creating %s" % model)
            yield tables.runCreateTable(model, transactor, database)
        except Exception, e:
            log.debug(str(e))


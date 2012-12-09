# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE
"""
In here we shall keep track of all variables and objects that should be
instantiated only once and be common to pieces of GLBackend code.
"""
__all__ = ['database', 'db_threadpool']

from twisted.python.threadpool import ThreadPool

from storm.uri import URI
from storm.twisted.transact import Transactor
from storm.databases.sqlite import SQLite

__version__ = '0.0.1'

from oonib import config

database = SQLite(URI(config.main.database_uri))
db_threadpool = ThreadPool(0, config.main.db_threadpool_size)
db_threadpool.start()
transactor = Transactor(db_threadpool)

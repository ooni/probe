from ooni.utils import Storage
from ooni.utils.config import Config

config = Storage()
config.main = Config('main', 'oonibackend.conf')
config.daphn3 = Config('daphn3', 'oonibackend.conf')

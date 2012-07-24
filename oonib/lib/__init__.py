from ooni.utils import Storage
from ooni.utils.config import Config
import os

root = os.path.normpath(os.path.join(os.path.realpath(__file__), '../../'))
config = Storage()
config.main = Config('main', os.path.join(root, 'oonibackend.conf'))
config.daphn3 = Config('daphn3', os.path.join(root, 'oonibackend.conf'))

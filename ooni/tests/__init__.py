import socket
from ooni.settings import config

config.initialize_ooni_home('ooni_home')
config.read_config_file()
config.logging = False
config.advanced.debug = False


def is_internet_connected():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(('torproject.org', 80))
        s.shutdown(2)
        return True
    except Exception:
        return False

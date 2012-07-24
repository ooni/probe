from twisted.internet import ssl
from oonib.lib import config

class SSLContext(ssl.DefaultOpenSSLContextFactory):
    def __init__(self, *args, **kw):
        ssl.DefaultOpenSSLContextFactory.__init__(self, config.main.ssl_private_key,
                                                  config.main.ssl_certificate)


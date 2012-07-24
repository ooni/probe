from twisted.internet import ssl

class SSLContext(ssl.DefaultOpenSSLContextFactory):
    def __init__(self, config):
        ssl.DefaultOpenSSLContextFactory.__init__(self, config.main.ssl_private_key,
                                                  config.main.ssl_certificate)


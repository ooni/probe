from twisted.internet import reactor
from ooni.common.txextra import HTTPConnectionPool

from twisted import version as twisted_version
from twisted.python.versions import Version
_twisted_15_0 = Version('twisted', 15, 0, 0)

from txsocksx.http import SOCKS5Agent
from txsocksx.client import SOCKS5ClientFactory

SOCKS5ClientFactory.noisy = False

class TrueHeadersSOCKS5Agent(SOCKS5Agent):
    def __init__(self, *args, **kw):
        super(TrueHeadersSOCKS5Agent, self).__init__(*args, **kw)
        pool = HTTPConnectionPool(reactor, False)
        #
        # With Twisted > 15.0 txsocksx wraps the twisted agent using a
        # wrapper class, hence we must set the _pool attribute in the
        # inner class rather than into its external wrapper.
        #
        if twisted_version >= _twisted_15_0:
            self._wrappedAgent._pool = pool
        else:
            self._pool = pool

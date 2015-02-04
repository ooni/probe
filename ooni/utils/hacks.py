# When some software has issues and we need to fix it in a
# hackish way, we put it in here. This one day will be empty.

import copy_reg
from twisted.web.client import SchemeNotSupported

from txsocksx.http import SOCKS5Agent as SOCKS5AgentOriginal


def patched_reduce_ex(self, proto):
    """
    This is a hack to overcome a bug in one of pythons core functions. It is
    located inside of copy_reg and is called _reduce_ex.

    Some background on the issue can be found here:

    http://stackoverflow.com/questions/569754/how-to-tell-for-which-object-attribute-pickle
    http://stackoverflow.com/questions/2049849/why-cant-i-pickle-this-object

    There was also an open bug on the pyyaml trac repo, but it got closed because
    they could not reproduce.
    http://pyyaml.org/ticket/190

    It turned out to be easier to patch the python core library than to monkey
    patch yaml.

    XXX see if there is a better way. sigh...
    """
    _HEAPTYPE = 1 << 9
    assert proto < 2
    for base in self.__class__.__mro__:
        if hasattr(base, '__flags__') and not base.__flags__ & _HEAPTYPE:
            break
    else:
        base = object  # not really reachable
    if base is object:
        state = None
    elif base is int:
        state = None
    else:
        if base is self.__class__:
            raise TypeError("can't pickle %s objects" % base.__name__)
        state = base(self)
    args = (self.__class__, base, state)
    try:
        getstate = self.__getstate__
    except AttributeError:
        if getattr(self, "__slots__", None):
            raise TypeError("a class that defines __slots__ without "
                            "defining __getstate__ cannot be pickled")
        try:
            dict = self.__dict__
        except AttributeError:
            dict = None
    else:
        dict = getstate()
    if dict:
        return copy_reg._reconstructor, args, dict
    else:
        return copy_reg._reconstructor, args


class SOCKS5Agent(SOCKS5AgentOriginal):
    """
    This is a quick hack to fix:
    https://github.com/habnabit/txsocksx/issues/9
    """
    def _getEndpoint(self, scheme_or_uri, host=None, port=None):
        if host is not None:
            scheme = scheme_or_uri
        else:
            scheme = scheme_or_uri.scheme
            host = scheme_or_uri.host
            port = scheme_or_uri.port
        if scheme not in ('http', 'https'):
            raise SchemeNotSupported('unsupported scheme', scheme)
        endpoint = self.endpointFactory(
            host, port, self.proxyEndpoint, **self.endpointArgs)
        if scheme == 'https':
            if hasattr(self, '_wrapContextFactory'):
                tlsPolicy = self._wrapContextFactory(host, port)
            elif hasattr(self, '_policyForHTTPS'):
                tlsPolicy = self._policyForHTTPS.creatorForNetloc(host, port)
            else:
                raise NotImplementedError("can't figure out how to make a context factory")
            endpoint = self._tlsWrapper(tlsPolicy, endpoint)
        return endpoint

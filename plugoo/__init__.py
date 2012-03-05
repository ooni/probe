# -*- coding: UTF-8
"""
    plugoo
    ******

    This contains all of the "goo" necessary for creating
    ooni-probe plugoonies.

    :copyright: (c) 2012 by Arturo Filastò.
    :license: see LICENSE for more details.

"""

__all__ = ['assets', 'reports', 'nodes']

import os
from datetime import datetime
import yaml

try:
    import socks
except:
    "Error SocksiPy is not installed!"
import socket

import logging
import itertools
import gevent

class torify(object):
    """This is the torify decorator. It should be used to
    decorate functions that should use to for connecting to
    the interwebz. The suggary syntax is the following:
    @torify([urllib2])
    def myfunction():
        f = urllib2.urlopen('https://torproject.org/')
    remember to set the proxyaddress in the config file.
    """
    def __init__(self, f):
        print f
        self.f = f

    def __get__(self, instance, owner):
        self.modules = instance.modules
        def decorator(*args):
            print instance.config.main.proxyaddress
            host, port = instance.config.main.proxyaddress.split(":")
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, host, int(port))
            # Wrap the modules into socks
            for module in self.modules:
                socks.wrapmodule(module)
            return self.f(instance, *args)
        return decorator

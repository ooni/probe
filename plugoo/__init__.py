# -*- coding: UTF-8
"""
    plugoo
    ******

    This contains all of the "goo" necessary for creating
    ooni-probe plugoonies.

    :copyright: (c) 2012 by Arturo Filastò.
    :license: see LICENSE for more details.

"""

__all__ = ['assets', 'nodes', 'reports', 'tests']

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

def gen_headers(self, options="common"):
    """
    Returns a set of headers to be used when generating
    HTTP requests.

    :options specify what rules should be used for
             generating the headers.
             "common": choose a very common header set (default)
             "random": make the headers random
    """
    if options == "common":
        headers = [('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
         ('Accept-Charset', 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'),
         ('Accept-Encoding', 'gzip,deflate,sdch'),
         ('Accept-Language', 'en,en-US;q=0.8,it;q=0.6'),
         ('Cache-Control', 'max-age=0')
         ('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_2) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11')]
    elif options == "random":
        # XXX not implemented
        return False
    else:
        print "Error, unrecognized header generation options.."
        return False

    return headers


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

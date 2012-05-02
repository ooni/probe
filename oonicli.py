#!/usr/bin/env python
# -*- coding: UTF-8
#
#    oonicli
#    *******
#
#    :copyright: (c) 2012 by Arturo Filastò
#    :license: see LICENSE for more details.
#

from plugoo import tests

from twisted.python import usage

from twisted.plugin import getPlugins

from zope.interface.exceptions import BrokenImplementation
from zope.interface.exceptions import BrokenMethodImplementation
from zope.interface.verify import verifyObject
import plugins

def retrieve_plugoo():
    interface = tests.ITest
    d = {}
    error = False
    for p in getPlugins(interface, plugins):
        try:
            verifyObject(interface, p)
            d[p.shortName] = p
        except BrokenImplementation, bi:
            print "Plugin Broke"
            print bi
            error = True
        except BrokenMethodImplementation, bmi:
            print "Plugin Broke"
            error = True
    if error != False:
        print "Plugin Loaded!"
    return d

plugoo = retrieve_plugoo()

class Options(usage.Options):
    tests = plugoo.keys()
    subCommands = []
    for test in tests:
        subCommands.append([test, None, plugoo[test].arguments, "Run the %s test" % test])

    optParameters = [
        ['status', 's', 0, 'Show current state'],
        ['restart', 'r', None, 'Restart OONI'],
        ['node', 'n', 'localhost:31415', 'Select target node']
    ]

config = Options()
config.parseOptions()


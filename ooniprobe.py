#!/usr/bin/env python
# -*- coding: UTF-8
"""
    ooni-probe
    **********

    Open Observatory of Network Interference

    "The Net interprets censorship as damage and routes around it."
                    - John Gilmore; TIME magazine (6 December 1993)

    The goal of ooni-probe is to collect data about censorship around
    the world.

    :copyright: (c) 2012 by Arturo Filastò
    :license: see LICENSE for more details.
"""

import imp
import os
import sys
import argparse

from pprint import pprint

import plugoo
from utils import Storage, parse_asset, import_test, get_logger
from config import Config
from logo import getlogo

class ooni(object):
    """
    ooni-probe is a suite designed to run tests on your
    network to detect censorship.
    This is the main class that is used to start ooni probe
    select the assets and run tests.
    """
    def __init__(self):
        self.config = Storage()
        self.config.main = Config("main")
        self.config.tests = Config("tests")
        self.config.report = Config("report")

        self.logger = get_logger(self.config.main)

        self.logger.info("Started ooni-probe")

        self.assets = []
        self.get_assets()

        self.tests = Storage()
        #self.load_tests()

        self.runtests = self.config.tests.run.split(",")


    def get_assets(self):
        """
        Parse all the assets in the asset directory.
        Assets can optionaly contain the ooni-probe asset file
        format: #:<something> <something_else>, that will then
        be used to render the asset details to the user.
        It is also possible to have an asset file link to multiple
        other files.
        """
        for root, dir, files in os.walk(self.config.main.assetdir):
            for name in files:
                asset = os.path.join(root, name)
                self.assets.append(parse_asset(asset))

    def list_assets(self):
        """
        Enumerate all the assets in the directory specified
        in the config file
        """
        print "[-] There are a total of %s assets loaded" % len(self.assets)
        for asset in self.assets:
            print "    name: %s" % asset.name
            if asset.desc:
                print "    description: %s" % asset.desc
            if asset.files:
                print "    files: %s" % asset.files
            if asset.tests:
                print "    tests: %s" % asset.tests
            print ""

    def load_tests(self):
        """
        Iterate through the plugoos inside the folder specified by the
        config file and instantiate them.
        """
        pluginfiles = [fname[:-3] for fname in os.listdir(self.config.main.testdir)\
                         if fname.endswith(".py")]
        for fname in pluginfiles:
            test = Storage()
            test_name = fname
            if not self.config.main.testdir in sys.path:
                sys.path.insert(0, self.config.main.testdir)
            #print "Fname: %s\n__import__(%s)" % (fname, fname)
            #print sys.path
            module = __import__(fname)
            try:
                test.name = module.__plugoo__
                test.desc = module.__desc__
                test.module = module
            except Exception, e:
                self.logger.warning("Soft fail %s", e)
                test.name = test_name
                test.desc = ""
                test.module = module

            try:
                self.tests[test_name] = test
            except Exception, e:
                print "Failed to load the test %s %s" % (name, e)

    def list_tests(self):
        """
        Print the loaded plugoonis to screen
        """
        self.load_tests()
        print "[-] There are a total of %s tests available" % len(self.tests)
        for name, test in self.tests.items():
            print "    name: %s" % name
            if test.name:
                print "    long name: %s" % test.name
            if test.desc:
                print "    description: %s" % test.desc
            print ""


    def run_tests(self):
        """
        Run all the tests that have been loaded
        """
        self.load_tests()
        for name in self.runtests:
            self.logger.info("running %s" % name)
            try:
                self.tests[name].module.run(self)
            except Exception, e:
                self.logger.error("ERR: %s" % e)

    def run_test(self, test, asset=None):
        """
        Run a single test
        """
        self.load_tests()
        if asset:
            self.tests[test].module.run(self, asset)
        else:
            self.tests[test].module.run(self)

if __name__ == "__main__":

    o = ooni()

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=getlogo() +
                                     '\n\n Open Observatory of Network Interference.')

    parser.add_argument('-t', '--list-tests', help='List all the available tests',
                        action='store_true', dest='list_tests')

    parser.add_argument('-l', '--list-assets', help='List all the assets',
                        action='store_true', dest='list_assets')

    parser.add_argument('-r', '--run', help='Run a certain test', action='store')

    parser.add_argument('-a', '--asset', help='Use this asset for the test',
                        action='store')

    parser.add_argument('--runall', help='Run all the tests in the config',
                        action='store_true')

    args = parser.parse_args()

    if args.list_tests:
        o.list_tests()

    if args.list_assets:
        o.list_assets()

    if args.run:
        o.run_test(args.run, args.asset)

    elif args.runall:
        o.run_tests()

    elif len(sys.argv) < 2:
        parser.print_help()


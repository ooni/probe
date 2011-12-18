import imp
import os
from pprint import pprint

import plugoo
from utils import Storage, parse_asset, import_test
from config import Config

class ooni(object):
    def __init__(self):
        self.config = Storage()
        self.config.main = Config("main")
        self.config.tests = Config("tests")
        
        self.assets = []
        self.get_assets()
        
        self.tests = Storage()
        self.load_tests()
    
    def get_assets(self):
        for root, dir, files in os.walk(self.config.main.assetdir):
            for name in files:
                asset = os.path.join(root, name)
                self.assets.append(parse_asset(asset))
    
    def list_assets(self):
        print "[-] There are a total of %s assets loaded" % len(self.assets)
        for asset in self.assets:
            print "    name: %s" % asset.name
            print "    description: %s" % asset.desc
            print "    files: %s" % asset.files
            print "    tests: %s\n" % asset.tests
    
    def load_tests(self):
        for root, dir, files in os.walk(self.config.main.testdir):
            for name in files:
                test_name, test = import_test(name, self.config)

                if test:
                    self.tests[test_name] = test
                try:
                    pass
                except:
                    print "Failed to load the test %s" % name
                
    def list_tests(self):
        print "[-] There are a total of %s tests available" % len(self.tests)
        for name, test in self.tests.items():
            print "    name: %s" % name
            print "    long name: %s" % test.name
            print "    description: %s" % test.desc
    
    def run_tests(self):
        pass
    
    def run_test(self, test):
        pass
    
o = ooni()
o.list_assets()
o.list_tests()


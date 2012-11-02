#!/usr/bin/env python
#
# DNS tampering detection module
# by Jacob Appelbaum <jacob@appelbaum.net>
#
# This module performs multiple DNS tests.

import sys
import ooni.dnsooni

class DNS():
  def __init__(self, args):
    self.in_ = sys.stdin
    self.out = sys.stdout
    self.debug = False
    self.randomize = args.randomize

  def DNS_Tests(self):
    print "DNS tampering detection:"
    filter_name = "_DNS_Tests"
    tests = [ooni.dnsooni]
    for test in tests:
      for function_ptr in dir(test):
        if function_ptr.endswith(filter_name):
          filter_result = getattr(test, function_ptr)(self)
          if filter_result == True:
            print function_ptr + " thinks the network is clean"
          elif filter_result == None:
              print function_ptr + " failed"
          else:
            print function_ptr + " thinks the network is dirty"

  def main(self):
    for function_ptr in dir(self):
      if function_ptr.endswith("_Tests"):
        getattr(self, function_ptr)()

if __name__ == '__main__':
  self.main()

#!/usr/bin/env python
#
# DNS tampering detection module
# by Jacob Appelbaum <jacob@appelbaum.net>
#
# This module performs DNS queries against a known good resolver and a possible
# bad resolver. We compare every resolved name against a list of known filters
# - if we match, we ring a bell; otherwise, we list possible filter IP
# addresses. There is a high false positive rate for sites that are GeoIP load
# balanced.
#

import sys
import ooni.dnsooni

class DNSBulk():
  def __init__(self, args):
    self.in_ = sys.stdin
    self.out = sys.stdout
    self.randomize = args.randomize
    self.cc = args.cc
    self.debug = False

  # We run a specific country test or all of them
  def DNS_Tests(self):
    if self.cc:
      filter_name = "cc_DNS_Tests_" + str(self.cc)
    else:
      filter_name = "cc_DNS_Tests_"
    tests = [ooni.dnsooni]
    for test in tests:
      for function_ptr in dir(test):
        if function_ptr.startswith(filter_name):
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

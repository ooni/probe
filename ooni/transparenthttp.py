#!/usr/bin/env python
#
# Captive Portal Detection With Multi-Vendor Emulation
# by Jacob Appelbaum <jacob@appelbaum.net>
#
# This module performs multiple tests that match specific vendor
# mitm proxies

import sys
import ooni.http
import ooni.report

class TransparentHTTPProxy():
  def __init__(self, args):
    self.in_ = sys.stdin
    self.out = sys.stdout
    self.debug = False
    self.logger = ooni.report.Log().logger

  def TransparentHTTPProxy_Tests(self):
    print "Transparent HTTP Proxy:"
    filter_name = "_TransparentHTTP_Tests"
    tests = [ooni.http]
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

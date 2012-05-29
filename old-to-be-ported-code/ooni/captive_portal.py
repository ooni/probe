#!/usr/bin/env python
#
# Captive Portal Detection With Multi-Vendor Emulation
# by Jacob Appelbaum <jacob@appelbaum.net>
#
# This module performs multiple tests that match specific vendor captive
# portal tests. This is a basic internet captive portal filter tester written
# for RECon 2011.
#
# Read the following URLs to understand the captive portal detection process
# for various vendors:
#
# http://technet.microsoft.com/en-us/library/cc766017%28WS.10%29.aspx
# http://blog.superuser.com/2011/05/16/windows-7-network-awareness/
# http://isc.sans.org/diary.html?storyid=10312&
# http://src.chromium.org/viewvc/chrome?view=rev&revision=74608
# http://code.google.com/p/chromium-os/issues/detail?id=3281
# http://crbug.com/52489
# http://crbug.com/71736
# https://bugzilla.mozilla.org/show_bug.cgi?id=562917
# https://bugzilla.mozilla.org/show_bug.cgi?id=603505
# http://lists.w3.org/Archives/Public/ietf-http-wg/2011JanMar/0086.html
# http://tools.ietf.org/html/draft-nottingham-http-portal-02
#
# XXX TODO:
# Implement some specific "known bad" tests
#

import sys
import ooni.http
import ooni.dnsooni
import ooni.report

class CaptivePortal():
  def __init__(self, args):
    self.in_ = sys.stdin
    self.out = sys.stdout
    self.debug = False
    self.logger = ooni.report.Log().logger

  def CaptivePortal_Tests(self):
    print "Captive Portal Detection With Multi-Vendor Emulation:"
    filter_name = "_CP_Tests"
    tests = [ooni.http, ooni.dnsooni]
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

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

import sys
import ooni.http
import ooni.dnsooni
import ooni.report

from ooni.plugooni import Plugoo

class CaptivePortalPlugin(Plugoo):
  def __init__(self):
    self.in_ = sys.stdin
    self.out = sys.stdout
    self.debug = False
    self.logger = ooni.report.Log().logger
    self.name = ""
    self.type = ""
    self.paranoia = ""
    self.modules_to_import = []
    self.output_dir = ""
    self.default_args = ""

  def CaptivePortal_Tests(self):
    print "Captive Portal Detection With Multi-Vendor Emulation:"
    tests = self.get_tests_by_filter(("_CP_Tests"), (ooni.http, ooni.dnsooni))
    self.run_tests(tests)

  def magic_main(self):
    self.run_plgoo_tests("_Tests")

  def ooni_main(self,args):
    self.magic_main()

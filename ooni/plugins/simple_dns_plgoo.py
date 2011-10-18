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

from ooni.plugooni import Plugoo

class DNSBulkPlugin(Plugoo):
  def __init__(self):
    self.in_ = sys.stdin
    self.out = sys.stdout
    self.randomize = True # Pass this down properly
    self.debug = False

  def DNS_Tests(self):
    print "DNS tampering detection for list of domains:"
    tests = self.get_tests_by_filter(("_DNS_BULK_Tests"), (ooni.dnsooni))
    self.run_tests(tests)

  def magic_main(self):
    self.run_plgoo_tests("_Tests")

  def ooni_main(self, args):
    self.magic_main()


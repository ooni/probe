#!/usr/bin/env python
#
# Common functions for ooni-probe related tests
#

import random

def _randstring(bytes_min, bytes_max=None):
  if bytes_max == None:
    bytes_max = bytes_min
  bytes = random.randint(bytes_min, bytes_max)
  letters = "abcdefghijklmnopqrstuvwxyz"
  randstring =  ''.join(random.choice(letters) for r in xrange(bytes))
  return randstring


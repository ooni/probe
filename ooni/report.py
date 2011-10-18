#!/usr/bin/env python
#
# Reporting and logging
# by Jacob Appelbaum <jacob@appelbaum.net>
#    Arturo Filasto' <art@fuffa.org>

import ooni.common
import logging
import os

class Report:
  def __init__(self):
    self.location = ""

class Log():
  def __init__(self):
    self.location = os.getcwd() + "/reports/ooni.log"
    self.level = "DEBUG"
    logging.basicConfig(filename=self.location,level=eval("logging." + self.level),format='%(asctime)s: [%(levelname)s] %(message)s')
    self.logger = logging.getLogger('ooni')

   

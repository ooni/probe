#!/usr/bin/python
# This is a wrapper around the Netalyzer Java command line client
# by Jacob Appelbaum <jacob@appelbaum.net>
#
from ooni.plugooni import Plugoo
import time
import os

class NetalyzrPlugin(Plugoo):
  def __init__(self):
    self.name = "Netalyzr"
    self.type = "wrapper"
    self.paranoia = "low"
    self.modules_to_import = ["os", "time"]
    self.output_dir = "results/"
    self.program = "java -jar third-party/NetalyzrCLI.jar "
    self.test_token = time.asctime(time.gmtime()).replace(" ", "_").strip()
    self.output_file = self.output_dir + "NetalyzrCLI_" + self.test_token + ".out"
    self.output_file.strip()
    self.run_me = self.program + " 2>&1 >> " + self.output_file

  def NetalzrWrapper(self):
   return os.system(self.run_me)

  def ooni_main(self, cmd):
    print "running NetalzrWrapper"
    r = self.NetalzrWrapper()
    print "finished running NetalzrWrapper"
    return r


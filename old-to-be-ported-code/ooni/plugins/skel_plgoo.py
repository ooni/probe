#!/usr/bin/python
# This will never load it is just an example of Plugooni plgoo plugins
#
from ooni.plugooni import Plugoo

class SkelPlugin(Plugoo):
  def __init__(self):
    self.name = ""
    self.type = ""
    self.paranoia = ""
    self.modules_to_import = []
    self.output_dir = ""

  def ooni_main(self, cmd):
    print "This is the main plugin function"



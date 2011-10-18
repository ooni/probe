#!/usr/bin/env python
#
# Plugooni, ooni plugin module for loading plgoo files.
# by Jacob Appelbaum <jacob@appelbaum.net>
#    Arturo Filasto' <art@fuffa.org>

import sys
import os

class Yamlooni():
  def __init__(self, name, creator, location):
    self.name = name
    self.creator = creator
    self.location = location
    f = open(self.location)
    self.ydata = yaml.load(f.read())
  
  def debug_print():
    #print y.input
    for i in y.iteritems():
      if i[0] == "input":
        print "This is the input part:"
        for j in i[1].iteritems():
          print j
        print "end of the input part.\n"

      elif i[0] == "output":
        print "This is the output part:"
        for j in i[1].iteritems():
          print j
        print "end of the output part.\n"

      elif i[0] == "plugin":
        print "This is the Plugin part:"
        for j in i[1].iteritems():
          print j
        print "end of the plugin part.\n"




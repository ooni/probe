#!/usr/bin/env python
#
# Plugooni, ooni plugin module for loading plgoo files.
# by Jacob Appelbaum <jacob@appelbaum.net>
#    Arturo Filasto' <art@fuffa.org>

import sys
import os

import imp, pkgutil, inspect

class Plugoo:
  def __init__(self, name, plugin_type, paranoia, author):
    self.name = name
    self.author = author
    self.type = plugin_type
    self.paranoia = paranoia

  """
  Expect a tuple of strings in 'filters' and a tuple of ooni 'plugins'.
  Return a list of (plugin, function) tuples that match 'filter' in 'plugins'.
  """
  def get_tests_by_filter(self, filters, plugins):
    ret_functions = []

    for plugin in plugins:
     for function_ptr in dir(plugin):
       if function_ptr.endswith(filters):
         ret_functions.append((plugin,function_ptr))
    return ret_functions

  """
  Expect a list of (plugin, function) tuples that must be ran, and three strings 'clean'
  'dirty' and 'failed'.
  Run the tests and print 'clean','dirty' or 'failed' according to the test result.
  """
  def run_tests(self, tests, clean="clean", dirty="dirty", failed="failed"):
    for test in tests:
      filter_result = getattr(test[0], test[1])(self)
      if filter_result == True:
        print test[1] + ": " + clean
      elif filter_result == None:
        print test[1] + ": " + failed
      else:
        print test[1] + ": " + dirty

  """
  Find all the tests belonging to plgoo 'self' and run them.
  We know the tests when we see them because they end in 'filter'.
  """
  def run_plgoo_tests(self, filter):
    for function_ptr in dir(self):
      if function_ptr.endswith(filter):
        getattr(self, function_ptr)()

PLUGIN_PATHS = [os.path.join(os.getcwd(), "ooni", "plugins")]
RESERVED_NAMES = [ "skel_plgoo" ]

class Plugooni():
  def __init__(self, args):
    self.in_ = sys.stdin
    self.out = sys.stdout
    self.debug = False
    self.loadall = True
    self.plugin_name = args.plugin_name
    self.listfile = args.listfile

    self.plgoo_found = False

  # Print all the plugoons to stdout.
  def list_plugoons(self):
    print "Plugooni list:"
    for loader, name, ispkg in pkgutil.iter_modules(PLUGIN_PATHS):
      if name not in RESERVED_NAMES:
        print "\t%s" %(name.split("_")[0])

  # Return name of the plgoo class of a plugin.
  # We know because it always ends with "Plugin".
  def get_plgoo_class(self,plugin):
    for memb_name, memb in inspect.getmembers(plugin, inspect.isclass):
      if memb.__name__.endswith("Plugin"):
        return memb

  # This function is responsible for loading and running the plugoons
  # the user wants to run.
  def run(self, command_object):
    print "Plugooni: the ooni plgoo plugin module loader"

    # iterate all modules
    for loader, name, ispkg in pkgutil.iter_modules(PLUGIN_PATHS):
      # see if this module should be loaded
      if (self.plugin_name == "all") or (name == self.plugin_name+"_plgoo"):
        self.plgoo_found = True # we found at least one plgoo!

        file, pathname, desc = imp.find_module(name, PLUGIN_PATHS)
        # load module
        plugin = imp.load_module(name, file, pathname, desc)
        # instantiate plgoo class and call its ooni_main()
        self.get_plgoo_class(plugin)().ooni_main(command_object)

    # if we couldn't find the plgoo; whine to the user
    if self.plgoo_found is False:
      print "Plugooni could not find plugin '%s'!" %(self.plugin_name)

if __name__ == '__main__':
  self.main()

import pkgutil
import sys
from os import listdir, path

__all__ = ['txtorcon', 'txscapy', 'txtraceroute']

__sub_modules__ = [ ]

def callback(arg, directory, files):
    for file in listdir(directory):
        fullpath = path.abspath(file)
        if path.isdir(fullpath) and not path.islink(fullpath):
            __sub_modules__.append(fullpath)
            sys.path.append(fullpath)

path.walk(".", callback, None)

def load_submodules(init, list):
    for subdir in list:
        contents=[x for x in pkgutil.iter_modules(path=subdir, 
                                                  prefix='ooni.lib.')]
        for loader, module_name, ispkg in contents:
            init_dot_module = init + "." + module_name
            if init_dot_module in sys.modules:
                module = sys.modules[module_name]
            else:
                if module_name in __all__:
                    grep = loader.find_module(module_name)
                    module = grep.load_module(module_name)
                else:
                    module = None

            if module is not None:
                globals()[module_name] = module

load_submodules(__name__, __sub_modules__)

print "system paths are: %s" % sys.path
print "globals are: %s" % globals()
print "system modules are: %s" % sys.modules

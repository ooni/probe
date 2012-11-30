# -*- encoding: utf-8 -*-
#
# hacks.py
# ********
# When some software has issues and we need to fix it in a
# hackish way, we put it in here. This one day will be empty.
# 
# :authors: Arturo Filastò
# :licence: see LICENSE

from yaml.representer import *
from yaml.emitter import *
from yaml.serializer import *
from yaml.resolver import *

import copy_reg

def patched_reduce_ex(self, proto):
    """
    This is a hack to overcome a bug in one of pythons core functions. It is
    located inside of copy_reg and is called _reduce_ex.

    Some background on the issue can be found here:

    http://stackoverflow.com/questions/569754/how-to-tell-for-which-object-attribute-pickle
    http://stackoverflow.com/questions/2049849/why-cant-i-pickle-this-object

    There was also an open bug on the pyyaml trac repo, but it got closed because
    they could not reproduce.
    http://pyyaml.org/ticket/190

    It turned out to be easier to patch the python core library than to monkey
    patch yaml.

    XXX see if there is a better way. sigh...
    """
    _HEAPTYPE = 1<<9
    assert proto < 2
    for base in self.__class__.__mro__:
        if hasattr(base, '__flags__') and not base.__flags__ & _HEAPTYPE:
            break
    else:
        base = object # not really reachable
    if base is object:
        state = None
    elif base is int:
        state = None
    else:
        if base is self.__class__:
            raise TypeError, "can't pickle %s objects" % base.__name__
        state = base(self)
    args = (self.__class__, base, state)
    try:
        getstate = self.__getstate__
    except AttributeError:
        if getattr(self, "__slots__", None):
            raise TypeError("a class that defines __slots__ without "
                            "defining __getstate__ cannot be pickled")
        try:
            dict = self.__dict__
        except AttributeError:
            dict = None
    else:
        dict = getstate()
    if dict:
        return copy_reg._reconstructor, args, dict
    else:
        return copy_reg._reconstructor, args

class OSafeRepresenter(SafeRepresenter):
    """
    This is a custom YAML representer that allows us to represent reports
    safely.
    It extends the SafeRepresenter to be able to also represent complex numbers
    """
    def represent_complex(self, data):
        if data.imag == 0.0:
            data = u'%r' % data.real
        elif data.real == 0.0:
            data = u'%rj' % data.imag
        elif data.imag > 0:
            data = u'%r+%rj' % (data.real, data.imag)
        else:
            data = u'%r%rj' % (data.real, data.imag)
        return self.represent_scalar(u'tag:yaml.org,2002:python/complex', data)

OSafeRepresenter.add_representer(complex,
                                 OSafeRepresenter.represent_complex)

class OSafeDumper(Emitter, Serializer, OSafeRepresenter, Resolver):
    """
    This is a modification of the YAML Safe Dumper to use our own Safe
    Representer that supports complex numbers.
    """
    def __init__(self, stream,
            default_style=None, default_flow_style=None,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None):
        Emitter.__init__(self, stream, canonical=canonical,
                indent=indent, width=width,
                allow_unicode=allow_unicode, line_break=line_break)
        Serializer.__init__(self, encoding=encoding,
                explicit_start=explicit_start, explicit_end=explicit_end,
                version=version, tags=tags)
        OSafeRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style)
        Resolver.__init__(self)

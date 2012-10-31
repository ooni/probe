# -*- encoding: utf-8 -*-
#
# :authors: Arturo Filastò
# :licence: see LICENSE

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

class MetaSuper(type):
    """
    Metaclass for creating subclasses which have builtin name munging, so that
    they are able to call self.__super.method() from an instance function
    without knowing the instance class' base class name.

    For example:

        from hacks import MetaSuper
        class A:
            __metaclass__ = MetaSuper
            def method(self):
                return "A"
        class B(A):
            def method(self):
                return "B" + self.__super.method()
        class C(A):
            def method(self):
                return "C" + self.__super.method()
        class D(C, B):
            def method(self):
                return "D" + self.__super.method()

        assert D().method() == "DCBA"

    Subclasses should not override "__init__", nor should subclasses have
    the same name as any of their bases, or else much pain and suffering
    will occur.
    """
    def __init__(cls, name, bases, dict):
        super(autosuper, cls).__init__(name, bases, dict)
        setattr(cls, "_%s__super" % name, super(cls))

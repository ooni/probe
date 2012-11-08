#-*- coding: utf-8 -*-
#
# assertions.py
# -------------
# Collection of utilies for checks and assertions.
#
# :authors: Isis Lovecruft
# :version: 0.1.0-alpha
# :license: see included LICENSE file
# :copyright: 2012 Isis Lovecruft, The Tor Project Inc.
#

def isNewStyleClass(obj):
    """
    Check if :param:`obj` is a new-style class, which is any class
    derived by either

        NewStyleClass = type('NewStyleClass')
    or
        class NewStyleClass(object):
            pass

    whereas old-style classes are (only in Python 2.x) derived by:

        class OldStyleClass:
            pass

    There are recently implemented classes in many Python libraries,
    including a few in Twisted, which are derived from old-style classes.
    Thus, calling super() or attempting to retrieve the MRO of any
    subclass of old-style classes can cause issues such as:

      o Calling Subclass.mro() goes through the class hierarchy until it
        reaches OldStyleClass, which has no mro(), and raises an
        AttributeError.

      o Calling super(Subclass, subcls) produces an ambiguous, rather than
        algorithmic, class hierarchy, which (especially in Twisted's case)
        breaks multiple inheritance.

      o Expected Subclass instance attributes, in particular __bases__ and
        __class__, can be missing, which in turn leads to problems with
        a whole bunch of builtin methods and modules.

    For more information, see:
    http://www.python.org/download/releases/2.3/mro/
    http://www.cafepy.com/article/python_attributes_and_methods/

    :return:
        True if :param:`obj` is a new-style class derived from object;
        False if :param:`obj` is an old-style class (or derived from
        one).
    """
    from types import ClassType
    return not isinstance(type(object), ClassType)

def isOldStyleClass(obj):
    """
    Check if :param:`obj` is an old-style class, which is any class
    derived in Python 2.x with:

        class OldStyleClass:
            pass

    There are recently implemented classes in many Python libraries,
    including a few in Twisted, which are derived from old-style classes,
    and thus their types, bases, and attributes are generally just messed
    up.

    :return:
        True if :param:`obj` is a new-style class derived from object;
        False if :param:`obj` is an old-style class (or derived from
        one).
    """
    from types import ClassType
    return not isinstance(type(object), ClassType)

def isClass(obj):
    """
    Check if an object is *a* class (not a specific class), without trying
    to call the obj.__class__ attribute, as that is not available in some
    cases. This function will return True for both old- and new-style
    classes, however, it will return False for class instances of either
    style. An alternate way to do this (although it presumes that
    :param:`obj` is a class instance) would be:

       from types import TypeType
       return isinstance(object.__class__, TypeType)

    It turns out that objects with <type 'type'>, i.e. classes, don't
    actually have the __class__ attribute...go figure. Instead, class
    objects are only required to have the __doc__ and __module__
    attributes.

    :param obj:
        Any object.
    :return:
        True if :param:`obj` is a class, False if otherwise (even if
        :param:`obj` is an instance of a class).
    """
    from types import ClassType
    return isinstance(object, (type, ClassType))

def isNotClass(object):
    """
    See :func:`isClass`.
    """
    return True if not isClass(object) else False

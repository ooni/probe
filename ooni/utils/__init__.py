"""

"""

import imp
import os
import logging
import string
import random
import yaml

class Storage(dict):
    """
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.

        >>> o = Storage(a=1)
        >>> o.a
        1
        >>> o['a']
        1
        >>> o.a = 2
        >>> o['a']
        2
        >>> del o.a
        >>> o.a
        None
    """
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, k:
            return None

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, k:
            raise AttributeError, k

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, value):
        for (k, v) in value.items():
            self[k] = v

class PermissionsError(Exception):
    """This test requires administrator or root permissions."""

def checkForRoot():
    """Check permissions."""
    if os.getuid() != 0:
        raise PermissionsError

def randomSTR(length, num=True):
    """
    Returns a random, all-uppercase, alpha-numeric (if num=True), string of
    specified character length.
    """
    chars = string.ascii_uppercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))

def randomstr(length, num=True):
    """
    Returns a random, all-lowercase, alpha-numeric (if num=True), string
    specified character length.
    """
    chars = string.ascii_lowercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))

def randomStr(length, num=True):
    """
    Returns a random a mixed lowercase, uppercase, alpha-numeric (if num=True)
    string of specified character length.
    """
    chars = string.ascii_lowercase + string.ascii_uppercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))

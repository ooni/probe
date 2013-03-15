import logging
import string
import random
import glob
import yaml
import imp
import os

from ooni import errors

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

def checkForRoot():
    if os.getuid() != 0:
        raise errors.InsufficientPrivileges

def randomSTR(length, num=True):
    """
    Returns a random all uppercase alfa-numerical (if num True) string long length
    """
    chars = string.ascii_uppercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))

def randomstr(length, num=True):
    """
    Returns a random all lowercase alfa-numerical (if num True) string long length
    """
    chars = string.ascii_lowercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))

def randomStr(length, num=True):
    """
    Returns a random a mixed lowercase, uppercase, alfanumerical (if num True)
    string long length
    """
    chars = string.ascii_lowercase + string.ascii_uppercase
    if num:
        chars += string.digits
    return ''.join(random.choice(chars) for x in range(length))


def pushFilenameStack(filename):
    """
    Takes as input a target filename and checks to see if a file by such name
    already exists. If it does exist then it will attempt to rename it to .1,
    if .1 exists it will rename .1 to .2 if .2 exists then it will rename it to
    .3, etc.
    This is similar to pushing into a LIFO stack.

    XXX: This will not work with stacks bigger than 10 elements because
    glob.glob(".*") will return them in the wrong order (a.1, a.11, a.2, a.3,
    etc.)
    This is probably not an issue since the only thing it causes is that files
    will be renamed in the wrong order and you shouldn't have the same report
    filename for more than 10 reports anyways, because you should be making
    ooniprobe generate the filename for you.

    Args:
        filename (str): the path to filename that you wish to create.
    """
    stack = glob.glob(filename+".*")
    for f in reversed(stack):
        c_idx = f.split(".")[-1]
        c_filename = '.'.join(f.split(".")[:-1])
        new_idx = int(c_idx) + 1
        new_filename = "%s.%s" % (c_filename, new_idx)
        os.rename(f, new_filename)
    os.rename(filename, filename+".1")



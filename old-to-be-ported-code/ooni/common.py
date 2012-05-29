#!/usr/bin/env python
#
# Common functions for ooni-probe related tests
#

import random
def _randstring(bytes_min, bytes_max=None):
  if bytes_max == None:
    bytes_max = bytes_min
  bytes = random.randint(bytes_min, bytes_max)
  letters = "abcdefghijklmnopqrstuvwxyz"
  randstring =  ''.join(random.choice(letters) for r in xrange(bytes))
  return randstring

class Storage(dict):
    """
    This code comes from web2py (http://web2py.org)
    A Storage object is like a dictionary except `obj.foo` can be used
    in addition to `obj['foo']`.

        >>> o = Storage(a=1)
        >>> print o.a
        1

        >>> o['a']
        1

        >>> o.a = 2
        >>> print o['a']
        2

        >>> del o.a
        >>> print o.a
        None

    """

    def __getattr__(self, key):
        if key in self:
            return self[key]
        else:
            return None

    def __setattr__(self, key, value):
        if value == None:
            if key in self:
                del self[key]
        else:
            self[key] = value

    def __delattr__(self, key):
        if key in self:
            del self[key]
        else:
            raise AttributeError, "missing key=%s" % key

    def __repr__(self):
        return '<Storage ' + dict.__repr__(self) + '>'

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, value):
        for (k, v) in value.items():
            self[k] = v

    def getlist(self, key):
        """Return a Storage value as a list.

        If the value is a list it will be returned as-is.
        If object is None, an empty list will be returned.
        Otherwise, [value] will be returned.

        Example output for a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getlist('x')
        ['abc']
        >>> request.vars.getlist('y')
        ['abc', 'def']
        >>> request.vars.getlist('z')
        []

        """
        value = self.get(key, None)
        if isinstance(value, (list, tuple)):
            return value
        elif value is None:
            return []
        return [value]

    def getfirst(self, key):
        """Return the first or only value when given a request.vars-style key.

        If the value is a list, its first item will be returned;
        otherwise, the value will be returned as-is.

        Example output for a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getfirst('x')
        'abc'
        >>> request.vars.getfirst('y')
        'abc'
        >>> request.vars.getfirst('z')

        """
        value = self.getlist(key)
        if len(value):
            return value[0]
        return None

    def getlast(self, key):
        """Returns the last or only single value when given a request.vars-style key.

        If the value is a list, the last item will be returned;
        otherwise, the value will be returned as-is.

        Simulated output with a query string of ?x=abc&y=abc&y=def
        >>> request = Storage()
        >>> request.vars = Storage()
        >>> request.vars.x = 'abc'
        >>> request.vars.y = ['abc', 'def']
        >>> request.vars.getlast('x')
        'abc'
        >>> request.vars.getlast('y')
        'def'
        >>> request.vars.getlast('z')

        """
        value = self.getlist(key)
        if len(value):
            return value[-1]
        return None


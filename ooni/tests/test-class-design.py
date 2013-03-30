#!/usr/bin/env python
#
# testing classes to test multiple inheritance.
# these are not meant to be run by trial, though they could be made to be so.
# i didn't know where to put them. --isis

import abc
from pprint import pprint
from inspect import classify_class_attrs

class PluginBase(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def name(self):
        return 'you should not see this'

    @name.setter
    def name(self, value):
        return 'you should not set this'

    @name.deleter
    def name(self):
        return 'you should not del this'

    @abc.abstractmethod
    def inputParser(self, line):
        """Do something to parse something."""
        return

class Foo(object):
    woo = "this class has some shit in it"
    def bar(self):
        print "i'm a Foo.bar()!"
        print woo

class KwargTest(Foo):
    _name = "isis"

    #def __new__(cls, *a, **kw):
    #    return super(KwargTest, cls).__new__(cls, *a, **kw)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    def __init__(self, *a, **kw):
        super(KwargTest, self).__init__()

        ## this causes the instantion args to override the class attrs
        for key, value in kw.items():
            setattr(self.__class__, key, value)

        print "%s.__init__(): self.__dict__ = %s" \
            % (type(self), pprint(type(self).__dict__))

        for attr in classify_class_attrs(self):
            print attr

    @classmethod
    def sayname(cls):
        print cls.name

class KwargTestChild(KwargTest):
    name = "arturo"
    def __init__(self):
        super(KwargTestChild, self).__init__()
        print self.name

class KwargTestChildOther(KwargTest):
    def __init__(self, name="robot", does="lasers"):
        super(KwargTestChildOther, self).__init__()
        print self.name


if __name__ == "__main__":
    print "class KwargTest attr name: %s" % KwargTest.name
    kwargtest = KwargTest()
    print "KwargTest instantiated wo args"
    print "kwargtest.name: %s" % kwargtest.name
    print "kwargtest.sayname(): %s" % kwargtest.sayname()
    kwargtest2 = KwargTest(name="lovecruft", does="hacking")
    print "KwargTest instantiated with name args"
    print "kwargtest.name: %s" % kwargtest2.name
    print "kwargtest.sayname(): %s" % kwargtest2.sayname()

    print "class KwargTestChild attr name: %s" % KwargTestChild.name
    kwargtestchild = KwargTestChild()
    print "KwargTestChild instantiated wo args"
    print "kwargtestchild.name: %s" % kwargtestchild.name
    print "kwargtestchild.sayname(): %s" % kwargtestchild.sayname()

    print "class KwargTestChildOther attr name: %s" % KwargTestChildOther.name
    kwargtestchildother = KwargTestChildOther()
    print "KwargTestChildOther instantiated wo args"
    print "kwargtestchildother.name: %s" % kwargtestchildother.name
    print "kwargtestchildother.sayname(): %s" % kwargtestchildother.sayname()

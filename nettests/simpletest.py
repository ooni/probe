#-*- coding: utf-8 -*-
"""Contains classes for testing the basic functionality of oonicli."""

from ooni import nettest

class SimpleTest(nettest.NetTestCase):
    """
    A very simple test which prints integers, for testing that oonicli is
    working correctly.
    """
    inputs = range(0, 20)
    optParameters = [['asset', 'a', None, 'Asset file'],
                     ['controlserver', 'c', 'google.com',
                      'Specify the control server'],
                     ['resume', 'r', 0, 'Resume at this index'],
                     ['other', 'o', None, 'Other arguments']]
    def test_foo(self):
        """Test that tests are working."""
        print "Running %s with %s" % ("test_foo", self.input)
        self.report['test_foo'] = 'Antani'
        self.report['shared'] = "sblinda"

    def test_f4oo(self):
        """Test that tests are working."""
        print "Running %s with %s" % ("test_f4oo", self.input)
        self.report['test_f4oo'] = 'Antani'
        self.report['shared'] = "sblinda2"

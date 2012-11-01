from ooni import nettest
class SimpleTest(nettest.TestCase):
    inputs = range(1,100)
    optParameters = [['asset', 'a', None, 'Asset file'],
                     ['controlserver', 'c', 'google.com', 'Specify the control server'],
                     ['resume', 'r', 0, 'Resume at this index'],
                     ['other', 'o', None, 'Other arguments']]
    def test_foo(self, *arg, **kw):
        print "Running %s with %s" % ("test_foo", self.input)
        self.report['test_foo'] = 'Antani'
        self.report['shared'] = "sblinda"
        self.assertEqual(1,1)

    def test_f4oo(self, *arg, **kw):
        print "Running %s with %s" % ("test_f4oo", self.input)
        self.report['test_f4oo'] = 'Antani'
        self.report['shared'] = "sblinda2"
        self.assertEqual(1,1)

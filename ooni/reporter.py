from twisted.trial import reporter

class OONIReporter(reporter.Reporter):

    def startTest(self, test, input=None):
        print "Running %s" % test
        print "Input %s" % input
        self._input = input
        super(OONIReporter, self).startTest(test)



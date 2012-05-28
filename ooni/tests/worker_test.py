from twisted.internet import reactor
from plugoo import work, tests

class StupidAsset(object):
    def __init__(self):
        self.idx = 0

    def __iter__(self):
        return self

    def next(self):
        if self.idx > 30:
            raise StopIteration
        self.idx += 1
        return self.idx

wgen = work.WorkGenerator(StupidAsset, tests.StupidTest(None, None, None, None), {'bla': 'aaa'}, start=0)
worker = work.Worker()
for x in wgen:
    print "------"
    print "Work unit"
    print "------"
    worker.push(x)
    print "------"

reactor.run()


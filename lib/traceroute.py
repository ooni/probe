import sys
import socket
from twisted.internet import defer
from twisted.internet import reactor
from twisted.internet import threads

from txtraceroute import traceroute

def run(target, src_port, dst_port):
    res = []
    @defer.inlineCallbacks
    def start_trace(target, **settings):
        hops = yield traceroute(target, **settings)
        for hop in hops:
            res.append(hop.get())
        reactor.stop()

    settings = dict(hop_callback=None,
                    timeout=2,
                    max_tries=3,
                    max_hops=30, proto="tcp")
    try:
        target = socket.gethostbyname(target)
    except Exception, e:
        print("could not resolve '%s': %s" % (target, str(e)))
        sys.exit(1)

    reactor.callWhenRunning(start_trace, target, **settings)
    reactor.run()
    return res

print run("8.8.8.8", 80, 80)

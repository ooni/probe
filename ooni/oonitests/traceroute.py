try:
    from dns import resolver
except:
    print "Error: dnspython is not installed (http://www.dnspython.org/)"
import gevent
import os
import plugoo

try:
    import scapy
except:
    print "Error: traceroute plugin requires scapy to be installed (http://www.secdev.org/projects/scapy)"

from plugoo.assets import Asset
from plugoo.tests import Test

import socket

__plugoo__ = "Traceroute"
__desc__ = "Performs TTL walking tests"

class TracerouteAsset(Asset):
    def __init__(self, file=None):
        self = Asset.__init__(self, file)


class Traceroute(Test):
    """A *very* quick and dirty traceroute implementation, UDP and TCP
    """
    def traceroute(self, dst, dst_port=3880, src_port=3000, proto="tcp", max_hops=30):
        dest_addr = socket.gethostbyname(dst)
        print "Doing traceroute on %s" % dst

        recv = socket.getprotobyname('icmp')
        send = socket.getprotobyname(proto)
        ttl = 1
        while True:
            recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, recv)
            if proto == "tcp":
                send_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, send)
            else:
                send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, send)
            recv_sock.settimeout(10)
            send_sock.settimeout(10)

            send_sock.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)
            recv_sock.bind(("", src_port))
            if proto == "tcp":
                try:
                    send_sock.settimeout(2)
                    send_sock.connect((dst, dst_port))
                except socket.timeout:
                    pass

                except Exception, e:
                    print "Error doing connect %s" % e
            else:
                send_sock.sendto("", (dst, dst_port))

            curr_addr = None
            try:
                print "receiving data..."
                _, curr_addr = recv_sock.recvfrom(512)
                curr_addr = curr_addr[0]

            except socket.error, e:
                print "SOCKET ERROR: %s" % e

            except Exception, e:
                print "ERROR: %s" % e

            finally:
                send_sock.close()
                recv_sock.close()

            if curr_addr is not None:
                curr_host = "%s" % curr_addr
            else:
                curr_host = "*"

            print "%d\t%s" % (ttl, curr_host)

            if curr_addr == dest_addr or ttl > max_hops:
                break

            ttl += 1


    def experiment(self, *a, **kw):
        # this is just a dirty hack
        address = kw['data'][0]

        self.traceroute(address)

def run(ooni):
    """Run the test"""
    config = ooni.config
    urls = []

    traceroute_experiment = TracerouteAsset(os.path.join(config.main.assetdir, \
                                            config.tests.traceroute))

    assets = [traceroute_experiment]

    traceroute = Traceroute(ooni)
    ooni.logger.info("starting traceroute test")
    traceroute.run(assets)
    ooni.logger.info("finished")



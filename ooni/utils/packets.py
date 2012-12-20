# -*- coding: utf-8 -*-

'''
 packet.py
 ---------
 Utilities for building and working with packets with Scapy.

 @authors: Isis Lovecruft
 @license: see included LICENSE file
 @version: 0.0.8-alpha
'''


def build(resources=[], count=1):
    """
    Construct a list of packets to send out using a callable function
    :param:`constructor` which takes a list of (tuples of) data to use to
    build each packet.

    @param resources:
        A list or tuple of data to use in packet construction. If multiple
        data points are required, e.g. an IP address and a port, then
        resources should be a list of tuples. Example:
            [('1.1.1.1', 443), ('2.2.2.2', 80)]

    @param count:
        The number of packets to build for each resource in
        :param:`resource_list`. For example, if your :param:`constructor`
        creates a TCP SYN packet for each resource, setting count=5 would
        create five TCP SYN packets for each resource.

    @param constructor:
        A callable function for constructing packets, which has a signature of
        callable(resource, *args, **kwargs). Example:

            def constructor(resource, *args, **kwargs):
                from scapy.all import IP, TCP
                (addr, port) = resource
                return TCP(dport=port)/IP(dst=addr)
    """
    from functools import wraps
    from twisted.python.failure import Failure

    from ooni.utils import log

    if (isinstance(resources, list) or isinstance(resources, tuple)):
        _resources = resources
        log.debug("@build called with resources=%s" % _resources)
    else:
        _resources = []
        mesg = "@build should take list/tuple for parameter 'resources'."
        log.err(Exception(mesg))

    _count = 1 if ( count<1 or count>10000 ) else count
    if _count > 1:
        log.debug("@build called with count=%d" %_count)

    def decorator(constructor):
        """
        Decorator for calling constructor(resource, *args, **kwargs) for each
        resource, count number of times.
        """
        @wraps(constructor)
        def wrapper(*a, **kw):
            packets = []
            log.debug("@build calling %s args: %s kwargs: %s"
                      % (str(constructor.func_name), str(a), str(kw)))
            for resource in _resources:
                for x in xrange(_count):
                    packets.append(constructor(resource, *a, **kw))
            return packets
        return wrapper
    return decorator


## for debugging
if __name__ == "__main__":

    from scapy.all import IP, ICMP

    destinations = ['8.8.8.8', '127.0.0.1', '192.168.0.1']

    @build(destinations, 3)
    def make_icmp_packet(dest, foo):
        print "foo = %s" % foo
        return IP(dst=dest)/ICMP()

    plist = make_icmp_packet('bar')
    print plist

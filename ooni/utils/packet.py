# -*- coding: utf-8 -*-

'''
 packet.py
 ---------
 Utilities for building and working with packets with Scapy.

 @authors: Isis Lovecruft
 @license: see included LICENSE file
 @version: 0.0.8-alpha
'''

def build(resources):
    """
    Construct a list of packets to send out using a callable function
    :param:`constructor` which takes a list of (tuples of) data to use to
    build each packet.

    @param resources:
        A list or tuple of data to use in packet construction. If multiple
        data points are required, e.g. an IP address and a port, then
        resources should be a list of tuples. Example:
            [('1.1.1.1', 443), ('2.2.2.2', 80)]

    @func constructor:
        A callable function for constructing packets, which has a signature of
        callable(resource, *args, **kwargs). Example:

        resources = ['8.8.8.8', '127.0.0.1', '192.168.0.1']

        @count(3)
        @build(resources)
        def icmp_constructor(rsrc):
            return IP(dst=rsrc)/ICMP()
    """
    from functools import wraps
    from inspect import ismethod
    from twisted.python.failure import Failure

    from ooni.utils import log

    if (isinstance(resources, list) or isinstance(resources, tuple)):
        _resources = resources
        log.debug("@build called with resources=%s" % _resources)
    else:
        _resources = []
        mesg = "@build should take list/tuple for parameter 'resources'."
        log.err(Exception(mesg))

    def decorator(constructor):
        """
        Decorator for calling constructor(resource, *args, **kwargs) for each
        resource, count number of times. Works with methods and functions.
        """
        if ismethod(constructor):
            @wraps(constructor)
            def wrapper(self, *a, **kw): ## add 'self' if decorating a method
                packets = []
                log.debug("@build calling %s args: %s kwargs: %s"
                          % (str(constructor.im_func.func_name), str(a), str(kw)))
                for resource in _resources:
                    pkt = constructor(resource, *a, **kw)
                    packets.extend(list(pkt))
        else:
            @wraps(constructor)
            def wrapper(*a, **kw):
                packets = []
                log.debug("@build calling %s args: %s kwargs: %s"
                          % (str(constructor.func_name), str(a), str(kw)))
                for resource in _resources:
                    pkt = constructor(resource, *a, **kw)
                    packets.extend(list(pkt))
                return packets
        return wrapper
    return decorator

def count(num):
    """
    Decorator for building multiple copies of a packet per resource. This
    decorator, if used, should always come *before* the @build decorator.
    Example:
        @count(5)
        @build(resources)
        def tcp_constructor(rsrc, flags)
            from scapy.all import TCP, IP
            (addr, dport) = rsrc
            log.debug("Sending to %s:%s with flags=%s" % (addr, dport, flags))
            return TCP(dport=dport, flags=flags)/IP(dst=addr)

    @param num:
        The number of packets to build for each resource in
        :param:`resource_list`. For example, if your :param:`constructor`
        creates a TCP SYN packet for each resource, setting count=5 would
        create five TCP SYN packets for each resource.
    """
    from functools import wraps
    from ooni.utils import log

    _num = 1 if ( num<1 or num>10000 ) else num
    log.debug("@count = %d" % _num)

    def decorator(constructor):
        @wraps(constructor)
        def wrapper(*a, **kw):
            packets = []
            for x in xrange(_num):
                packets.extend([pkt for pkt in constructor(*a, **kw)])
            return packets
        return wrapper
    return decorator

def nicely(packets):
    """
    Print scapy summary nicely for a list of packets. Returns a list of
    packet.summary() for each packet.
    """
    return list([x.summary() for x in packets])


class NetTestResource(object):
    def __init__(self, ipaddr_or_domain=None, dport=None, *args, **kwargs):
        ## xxx finish
        raise NotImplemented

        if ipaddr_or_domain is not None:
           self.dst = ipaddr_or_domain
        if dport is not None:
            self.dport = dport
        if args:                           ## e.g. if we're given
            for arg in args:               ## 'checkSOA' as an arg,
                setattr(self, arg, True)   ## we set it to True
        if kwargs:
            for k,v in kwargs.items():
                setattr(self, k, v)


## for debugging
if __name__ == "__main__":
    from scapy.all import IP, ICMP, TCP
    from ooni.utils import log

    log.debug("Testing packet.py")

    resources = [('8.8.8.8', 443),
                 ('127.0.0.1', 0),
                 ('192.168.0.1', 80)]

    # test decorating functions:
    log.debug("Testing @build and @count decorators with function calls...")

    @count(3)
    @build(resources)
    def icmp_constructor(rsrc):
        log.debug("Testing build packet for %s" % rsrc[0])
        return IP(dst=rsrc[0])/ICMP()

    @count(5)
    @build(resources)
    def tcp_constructor(rsrc, flags):
        (addr, dport) = rsrc
        log.debug("Building packet for %s:%s with flags=%s"
                  % (addr, dport, flags))
        return TCP(dport=dport, flags=flags)/IP(dst=addr)

    icmp_list = icmp_constructor()
    tcp_list = tcp_constructor('S')

    assert isinstance(icmp_list, list), "icmp_constructor did not return list"
    assert isinstance(tcp_list, list), "tcp_constructor did not return list"
    assert len(icmp_list) == 9, "wrong number of packets generated"
    assert len(tcp_list) == 15, "wrong number of packets generated"

    log.debug("Generated ICMP packets:")
    log.debug("\n%s" % '\n'.join( [n for n in nicely(icmp_list)] ))
    log.debug("Generated TCP packets:")
    log.debug("\n%s" % '\n'.join( [n for n in nicely(tcp_list)] ))

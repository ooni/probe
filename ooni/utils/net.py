# -*- encoding: utf-8 -*-
#
# net.py
# --------
# OONI utilities for network infrastructure and hardware.
#
# :authors: Isis Lovecruft, Arturo Filasto
# :version: 0.0.1-pre-alpha
# :license: (c) 2012 Isis Lovecruft, Arturo Filasto
#           see attached LICENCE file

from pprint import pprint
from sys import platform

#if platformm.system() == 'Windows':
#    import _winreg as winreg

from ooni.utils import log

PLATFORMS = {'LINUX': platform.startswith("linux"),
             'OPENBSD': platform.startswith("openbsd"),
             'FREEBSD': platform.startswith("freebsd"),
             'NETBSD': platform.startswith("netbsd"),
             'DARWIN': platform.startswith("darwin"),
             'SOLARIS': platform.startswith("sunos"),
             'WINDOWS': platform.startswith("win32")}


class PlatformNameException(Exception):
    """Specified platform does not match client platform."""

class UnsupportedPlatform(Exception):
    """Support for this platform is not currently available."""

class IfaceError(Exception):
    """Could not find default network interface."""

class PermissionsError(SystemExit):
    """This test requires admin or root privileges to run. Exiting..."""

def getClientAddress():
    address = {'asn': 'REPLACE_ME',
               'ip': 'REPLACE_ME'}
    return address

def getClientPlatform(platform_name=None):
    for name, test in PLATFORMS.items():
        if not platform_name or platform_name.upper() == name:
            if test:
                return name, test

def getPosixIface():
    from twisted.internet.test import _posixifaces

    log.msg("Attempting to discover network interfaces...")
    ifaces = _posixifaces._interfaces()
    ifup = tryInterfaces(ifaces)
    return ifup

def getWindowsIface():
    from twisted.internet.test import _win32ifaces

    log.msg("Attempting to discover network interfaces...")
    ifaces = _win32ifaces._interfaces()
    ifup = tryInterfaces(ifaces)
    return ifup

def getPlatformAndIfaces(platform_name=None):
    client, test = getClientPlatform(platform_name)
    if client:
        if client == ('LINUX' or 'DARWIN') or client[-3:] == 'BSD':
            return getPosixIface()
        elif client == 'WINDOWS':
            return getWindowsIface()
        ## XXX fixme figure out how to get iface for Solaris
        else:
            return None
    else:
        raise UnsupportedPlatform

def checkInterfaces(ifaces=None, timeout=1):
    """
    @param ifaces:
        A dictionary in the form of ifaces['if_name'] = 'if_addr'.
    """
    try:
        from scapy.all import IP, ICMP
        from scapy.all import sr1   ## we want this check to be blocking
    except:
        log.msg(("Scapy required: www.secdev.org/projects/scapy"))

    ifup = {}
    if not ifaces:
        log.debug("net.checkInterfaces(): no interfaces specified!")
        return None

    for iface in ifaces:
        for ifname, ifaddr in iface:
            log.debug("net.checkInterfaces(): testing iface {} by pinging"
                      + " local address {}".format(ifname, ifaddr))
            try:
                pkt = IP(dst=ifaddr)/ICMP()
                ans, unans = sr(pkt, iface=ifname, timeout=5, retry=3)
            except Exception, e:
                raise PermissionsError if e.find("Errno 1") else log.err(e)
            else:
                if ans.summary():
                    log.debug("net.checkInterfaces(): got answer on interface %s"
                             + ":\n%s".format(ifname, ans.summary()))
                    ifup.update(ifname, ifaddr)
                else:
                    log.debug("Interface test packet was unanswered:\n%s"
                             % unans.summary())
    if len(ifup) > 0:
        log.msg("Discovered working network interfaces: %s" % ifup)
        return ifup
    else:
        raise IfaceError

def getNonLoopbackIfaces(platform_name=None):
    try:
        ifaces = getPlatformAndIfaces(platform_name)
    except UnsupportedPlatform, up:
        log.err(up)

    if not ifaces:
        log.msg("Unable to discover network interfaces...")
        return None
    else:
        found = [{i[0]: i[2]} for i in ifaces if i[0] != 'lo']
        log.debug("utils.net.getClientIfaces: Found non-loopback interfaces: %s"
                  % pprint(found))
        try:
            interfaces = checkInterfaces(found)
        except IfaceError, ie:
            log.err(ie)
            return None
        else:
            return interfaces

def getNetworksFromRoutes():
    from scapy.all import conf, ltoa
    from ipaddr    import IPNetwork, IPAddress

    ## Hide the 'no routes' warnings
    conf.verb = 0

    networks = []
    client   = conf.route
    log.debug("Local Routing Table:\n{}".format(client))

    for nw, nm, gw, iface, addr in client.routes:
        n = IPNetwork( ltoa(nw) )
        (n.netmask, n.gateway, n.ipaddr) = [IPAddress(x) for x in [nm, gw, addr]]
        n.iface = iface
        if not n.compressed in networks:
            networks.append(n)

    return networks

def getDefaultIface():
    networks = getNetworksFromRoutes()
    for net in networks:
        if net.is_private:
            return net
    raise IfaceError

def getLocalAddress():
    default_iface = getDefaultIface()
    return default_iface.ipaddr

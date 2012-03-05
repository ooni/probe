#!/usr/bin/env python
# -*- coding: UTF-8

import os
import sys
import socks

class Node(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port

"""
[]: node = NetworkNode("192.168.0.112", 5555, "SOCKS5")
[]: node_socket = node.wrap_socket()
"""
class NetworkNode(Node):
    def __init__(self, address, port, node_type="SOCKS5", auth_creds=None):
        self.node = Node(address,port)

        # XXX support for multiple types
        # node type (SOCKS proxy, HTTP proxy, GRE tunnel, ...)
        self.node_type = node_type
        # type-specific authentication credentials
        self.auth_creds = auth_creds

    def _get_socksipy_socket(self, proxy_type, auth_creds):
        import socks
        s = socks.socksocket()
        # auth_creds[0] -> username
        # auth_creds[1] -> password
        s.setproxy(proxy_type, self.node.address, self.node.port,
                   self.auth_creds[0], self.auth_creds[1])
        return s

    def _get_socket_wrapper(self):
        if (self.node_type.startswith("SOCKS")): # SOCKS proxies
            if (self.node_type != "SOCKS5"):
                proxy_type = socks.PROXY_TYPE_SOCKS5
            elif (self.node_type != "SOCKS4"):
                proxy_type = socks.PROXY_TYPE_SOCKS4
            else:
                print "We don't know this proxy type."
                sys.exit(1)

            return self._get_socksipy_socket(proxy_type)
        elif (self.node_type == "HTTP"): # HTTP proxies
            return self._get_socksipy_socket(PROXY_TYPE_HTTP)
        else: # Unknown proxies
            print "We don't know this proxy type."
            sys.exit(1)

    def wrap_socket(self):
        return self._get_socket_wrapper()

class CodeExecNode(Node):
    def __init__(self, address, port, node_type, auth_creds):
        self.node = Node(address,port)

        # node type (SSH proxy, etc.)
        self.node_type = node_type
        # type-specific authentication credentials
        self.auth_creds = auth_creds

    def add_unit(self):
        pass

    def get_status(self):
        pass



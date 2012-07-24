#!/usr/bin/env python
# -*- coding: UTF-8
"""
    nodes
    *****

    This contains all the code related to Nodes
    both network and code execution.

    :copyright: (c) 2012 by Arturo Filastò.
    :license: see LICENSE for more details.

"""

import os
from binascii import hexlify

try:
    import paramiko
except:
    print "Error: module paramiko is not installed."
from pprint import pprint
try:
    import pyXMLRPCssh
except:
    print "Error: module pyXMLRPCssh is not installed."
import sys
import socks
import xmlrpclib

class Node(object):
    def __init__(self, address, port):
        self.address = address
        self.port = port

class LocalNode(object):
    def __init__(self):
        pass

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

class PlanetLab(CodeExecNode):
    def __init__(self, address, auth_creds, ooni):
        self.auth_creds = auth_creds

        self.config = ooni.utils.config
        self.logger = ooni.logger
        self.name = "PlanetLab"

    def _api_auth(self):
        api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
        auth = {}
        ## should be changed to separate node.conf file
        auth['Username'] = self.config.main.pl_username
        auth['AuthString'] = self.config.main.pl_password
        auth['AuthMethod'] = "password"
        authorized = api_server.AuthCheck(auth)

        if authorized:
            print 'We are authorized!'
            return auth
        else:
            print 'Authorization failed. Please check your settings for pl_username and pl_password in the ooni-probe.conf file.'

    def _search_for_nodes(self, node_filter=None):
        api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/', allow_none=True)
        node_filter = {'hostname': '*.cert.org.cn'}
        return_fields = ['hostname', 'site_id']
        all_nodes = api_server.GetNodes(self.api_auth(), node_filter, boot_state_filter)
        pprint(all_nodes)
        return all_nodes

    def _add_nodes_to_slice(self):
        api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/', allow_none=True)
        all_nodes = self.search_for_nodes()
        for node in all_nodes:
            api_server.AddNode(self.api_auth(), node['site_id'], all_nodes)
            print 'Adding nodes %s' % node['hostname']

    def _auth_login(slicename, machinename):
        """Attempt to authenticate to the given PL node, slicename and
        machinename, using any of the private keys in ~/.ssh/ """

        agent = paramiko.Agent()
        agent_keys = agent.get_keys()
        if len(agent_keys) == 0:
            return

        for key in agent_keys:
            print 'Trying ssh-agent key %s' % hexlify(key.get_fingerprint()),
            try:
                paramiko.transport.auth_publickey(machinename, slicename)
                print 'Public key authentication to PlanetLab node %s successful.' % machinename,
                return
            except paramiko.SSHException:
                print 'Public key authentication to PlanetLab node %s failed.' % machinename,

    def _get_command():
        pass

    def ssh_and_run_(slicename, machinename, command):
        """Attempt to make a standard OpenSSH client to PL node, and run
        commands from a .conf file."""

        ## needs a way to specify 'ssh -l <slicename> <machinename>'
        ## with public key authentication.

        command = PlanetLab.get_command()

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.connect(machinename)

        stdin, stdout, stderr = client.exec_command(command)

    def send_files_to_node(directory, files):
        """Attempt to rsync a tree to the PL node."""
        pass

    def add_unit():
        pass

    def get_status():
        pass

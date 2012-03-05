#!/usr/bin/env python
"""
    planetlab.py
    ************

    Classes for using ooni-probe with PlanetLab nodes.
    
    :copyright: (c)2012 Isis Lovecruft
    :license: see LICENSE for more details
"""

from binascii import hexlify
from ooniprobe import ooni
import os
import xmlrpclib
import pprint
try:
    import paramiko
except:
    print "Error: paramiko module is not installed."
try:
    import pyXMLRPCssh
except:
    print "Error: pyXMLRPCssh module was not found. Please download and install from : https://pypi.python.org/pypi/pyXMLRPCssh/1.0-0"

class PlanetLab:
    
    """Defines a PlanetLab node"""
    
    ## should inherit from CODE EXEC NODE and NETWORK
    ## ADD UNIT OF WORK, adds the unit to pl's schedule
    ## needs GET STATUS method for reporting
    ## needs upload() and run() private methods

    def __init__(self, ooni):
        self.config = ooni.config
        self.logger = ooni.logger
        self.name = "PlanetLab"
    
    def api_auth(self):
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

    def search_for_nodes(self, boot_state_filter=None):
        api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
        boot_state_filter = {'hostname': '*.cert.org.cn'}
        all_nodes = api_server.GetNodes(self.api_auth(), boot_state_filter)
        pp = pprint.PrettyPrinter()
        pp.pprint(all_nodes)

    def auth_login(slicename, machinename):
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

    def make_client(slicename, machinename, command):
        """Attempt to make a standard OpenSSH client to PL node."""

        command = PlanetLab.get_command()
        
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.connect(machinename)

        stdin, stdout, stderr = client.exec_command(command)
        
    def send_files(files):
        """Attempt to rsync a tree to the PL node. Requires PyRsync:
        https://pypi.python.org/pypi/pyrsync/0.1.0"""
        pass
        
    def get_command:
        pass

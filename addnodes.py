#!/usr/bin/python
""" 
    addnodes.py
    ***********
    Script to add PlanetLab nodes to a slice. Takes an argument in the
    form of a dictionary boot_state_filter, which searches for nodes which
    match a pattern. Authentication patterns can be optionally defined in
    ooniprobe.config.

    :copyright: (c)2012 Isis Lovecruft
    :license: see LICENSE for more details
"""

from ooniprobe import ooni
try:
    import paramiko
except:
    "Error: paramiko module was not found."
import pprint
try:
    import pyXMLRPCssh
except:
    "Error: pyXMLRPCssh module was not found. Please download and install from: https://pypi.python.org/pypi/pyXMLRPCssh/1.0-0"
import xmlrpclib

class PlanetLab:
    def __init__(self, ooni):
        self.config = ooni.config
        self.logger = ooni.logger
        self.name = "PlanetLab"

    def api_auth(self):
        api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
        auth = {}
        auth['Username'] = self.config.main.pl_username
        auth['AuthString'] = self.config.main.pl_password
        auth['AuthMethod'] = "password"
        authorized = api_server.AuthCheck(auth)
        
        if authorized:
            print 'We are authorized!'
            return auth
        else:
            print 'Authorization failed. Please check the ooni-probe.conf file.'
            
    def search_for_nodes(self, boot_state_filter=None):
        api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
        boot_state_filter = {'hostname': '*.cert.org.cn'}
        all_nodes = api_server.GetNodes(self.api_auth(), boot_state_filter)
        pp = pprint.PrettyPrinter()
        pp.pprint(all_nodes)

def main():
    o = ooni()
    pl = PlanetLab(o)
    pl.search_for_nodes()

if __name__=="__main__":
    main()

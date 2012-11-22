#-*- coding: utf-8 -*-
#
# :authors: Arturo Filastò, Isis Lovecruft
# :license: see included LICENSE file
import os
import sys
import xmlrpclib

from fabric.api import run, cd, sudo

api_auth = {}
# Set these values 
api_auth['Username'] = "you@example.com"
api_auth['AuthString'] = "your_password"
slice_name = "your_slice_name"

### Do not change this
api_auth['AuthMethod'] = "password"

def search_node(nfilter="*.cert.org.cn"):
    api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
    if api_server.AuthCheck(api_auth):
        print "We are authenticated"
    else:
        print "We are not authenticated"
    node_filter = {'hostname': nfilter}
    return_fields = ['hostname', 'site_id']
    all_nodes = api_server.GetNodes(api_auth, node_filter, return_fields)
    print all_nodes

def add_node(nodeid):
    node_id = int(nodeid)
    api_server = xmlrpclib.ServerProxy('https://www.planet-lab.org/PLCAPI/')
    node_filter = {'node_id': node_id}
    return_fields = ['hostname', 'site_id']
    nodes = api_server.GetNodes(api_auth, node_filter, return_fields)
    print 'Adding nodes %s' % nodes
    api_server.AddNode(api_auth, node_id, slice_name)

def deployooniprobe(distro="debian"):
    """
    This is used to deploy ooni-probe on debian based systems.
    """
    run("git clone https://git.torproject.org/ooni-probe.git ooni-probe")
    cd("ooni-probe")
    if distro == "debian":
        sudo("apt-get install git-core python python-pip python-dev")
    else:
        print "The selected distro is not supported"
        print "The following commands may fail"
    run("virtualenv env")
    run("source env/bin/activate")
    run("pip install https://hg.secdev.org/scapy/archive/tip.zip")
    run("pip install -r requirements.txt")


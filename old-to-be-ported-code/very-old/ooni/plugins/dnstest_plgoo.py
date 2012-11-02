#!/usr/bin/python

import sys
import re
from pprint import pprint
from twisted.internet import reactor, endpoints
from twisted.names import client
from ooni.plugooni import Plugoo
from ooni.socksclient import SOCKSv4ClientProtocol, SOCKSWrapper

class DNSTestPlugin(Plugoo):
    def __init__(self):
        self.name = ""
        self.type = ""
        self.paranoia = ""
        self.modules_to_import = []
        self.output_dir = ""
        self.buf = ""
        self.control_response = []

    def response_split(self, response):
      a = []
      b = []
      for i in response:
        a.append(i[0])
        b.append(i[1])

      return a,b

    def cb(self, type, hostname, dns_server, value):
      if self.control_response is None:
        self.control_response = []
      if type == 'control' and self.control_response != value:
          print "%s %s" % (dns_server, value)
          self.control_response.append((dns_server,value))
          pprint(self.control_response)
      if type == 'experiment':
        pprint(self.control_response)
        _, res = self.response_split(self.control_response)
        if value not in res:
          print "res (%s) : " % value
          pprint(res)
          print "---"
          print "%s appears to be censored on %s (%s != %s)" % (hostname, dns_server, res[0], value)

        else:
          print "%s appears to be clean on %s" % (hostname, dns_server)
        self.r2.servers = [('212.245.158.66',53)]
      print "HN: %s %s" % (hostname, value)

    def err(self, pck, error):
      pprint(pck)
      error.printTraceback()
      reactor.stop()
      print "error!"
      pass

    def ooni_main(self, args):
        self.experimentalproxy = ''
        self.test_hostnames = ['dio.it']
        self.control_dns = [('8.8.8.8',53), ('4.4.4.8',53)]
        self.experiment_dns = [('85.37.17.9',53),('212.245.158.66',53)]

        self.control_res = []
        self.control_response = None

        self.r1 = client.Resolver(None, [self.control_dns.pop()])
        self.r2 = client.Resolver(None, [self.experiment_dns.pop()])

        for hostname in self.test_hostnames:
          for dns_server in self.control_dns:
            self.r1.servers = [dns_server]
            f = self.r1.getHostByName(hostname)
            pck = (hostname, dns_server)
            f.addCallback(lambda x: self.cb('control', hostname, dns_server, x)).addErrback(lambda x: self.err(pck, x))

          for dns_server in self.experiment_dns:
            self.r2.servers = [dns_server]
            pck = (hostname, dns_server)
            f = self.r2.getHostByName(hostname)
            f.addCallback(lambda x: self.cb('experiment', hostname, dns_server, x)).addErrback(lambda x: self.err(pck, x))

        reactor.run()


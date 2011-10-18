#!/usr/bin/python

import sys
import re
from twisted.internet import reactor, endpoints
from twisted.web import client
from ooni.plugooni import Plugoo
from ooni.socksclient import SOCKSv4ClientProtocol, SOCKSWrapper

class HttpPlugin(Plugoo):
    def __init__(self):
        self.name = ""
        self.type = ""
        self.paranoia = ""
        self.modules_to_import = []
        self.output_dir = ""
        self.buf = ''
        
    def cb(self, type, content):
        print "got %d bytes from %s" % (len(content), type) # DEBUG
        if not self.buf:
            self.buf = content
        else:
            if self.buf == content:
                print "SUCCESS"
            else:
                print "FAIL"
            reactor.stop()

    def endpoint(self, scheme, host, port):
        ep = None
        if scheme == 'http':
            ep = endpoints.TCP4ClientEndpoint(reactor, host, port)
        elif scheme == 'https':
            ep = endpoints.SSL4ClientEndpoint(reactor, host, port, context)
        return ep

    def ooni_main(self):
        # We don't have the Command object so cheating for now.
        url = 'http://check.torproject.org/'
        self.controlproxy = 'socks4a://127.0.0.1:9050'
        self.experimentalproxy = ''

        if not re.match("[a-zA-Z0-9]+\:\/\/[a-zA-Z0-9]+", url):
          return None
        scheme, host, port, path = client._parse(url)
        
        ctrl_dest = self.endpoint(scheme, host, port)
        if not ctrl_dest:
            raise Exception('unsupported scheme %s in %s' % (scheme, url))
        if self.controlproxy:
            _, proxy_host, proxy_port, _ = client._parse(self.controlproxy)
            control = SOCKSWrapper(reactor, proxy_host, proxy_port, ctrl_dest)
        else:
            control = ctrl_dest
        f = client.HTTPClientFactory(url)
        f.deferred.addCallback(lambda x: self.cb('control', x))
        control.connect(f)

        exp_dest = self.endpoint(scheme, host, port)
        if not exp_dest:
            raise Exception('unsupported scheme %s in %s' % (scheme, url))
        # FIXME: use the experiment proxy if there is one
        experiment = exp_dest
        f = client.HTTPClientFactory(url)
        f.deferred.addCallback(lambda x: self.cb('experiment', x))
        experiment.connect(f)
        
        reactor.run()

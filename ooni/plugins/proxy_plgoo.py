#!/usr/bin/python

import sys
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
            from twisted.internet import ssl
            ep = endpoints.SSL4ClientEndpoint(reactor, host, port,
                                              ssl.ClientContextFactory())
        return ep

    def ooni_main(self, cmd):
        # We don't have the Command object so cheating for now.
        url = cmd.hostname

        # FIXME: validate that url is on the form scheme://host[:port]/path
        scheme, host, port, path = client._parse(url)
        
        ctrl_dest = self.endpoint(scheme, host, port)
        if not ctrl_dest:
            raise Exception('unsupported scheme %s in %s' % (scheme, url))
        if cmd.controlproxy:
            assert scheme != 'https', "no support for proxied https atm, sorry"
            _, proxy_host, proxy_port, _ = client._parse(cmd.controlproxy)
            control = SOCKSWrapper(reactor, proxy_host, proxy_port, ctrl_dest)
            print "proxy: ", proxy_host, proxy_port
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

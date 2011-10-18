# -*- coding: utf-8
"""\
Command line UI module for ooni-probe - heavily inspired by Ingy döt Net
"""

import os
import sys
import re
import optparse

# Only include high level ooni tests at this time
import ooni.captive_portal
import ooni.namecheck
import ooni.dns_poisoning
import ooni.dns_cc_check
import ooni.transparenthttp
import ooni.helpers
import ooni.plugooni

class Command():
    def __init__(self, args):
        sys.argv = sys.argv[0:1]
        sys.argv.extend(args)
        self.startup_options()

    def startup_options(self):
        self.action = None
        self.from_ = None
        self.to = None
        self.parser = None
        self.emitter = None
        self.emit_header = None
        self.emit_trailer = None
        self.in_ = sys.stdin
        self.out = sys.stdout
        self.debug = False
        self.randomize = True
        self.cc = None
        self.hostname = None
        self.listfile = None
        self.listplugooni = False
        self.plugin_name = "all"
        self.controlproxy = None # "socks4a://127.0.0.1:9050/"
        self.experimentproxy = None

        usage = """

  'ooni' is the Open Observatory of Network Interference

        command line usage:  ooni-probe [options]"""

        optparser = optparse.OptionParser(usage=usage)

        # --plugin
        def cb_plugin(option, opt, value, oparser):
            self.action = opt[2:]
            self.plugin_name = str(value)
        optparser.add_option(
            "--plugin", type="string",
            action="callback", callback=cb_plugin,
            help="run the Plugooni plgoo plugin specified"
        )
 
        # --listplugins
        def cb_list_plugins(option, opt, value, oparser):
            self.action = opt[2:]
        optparser.add_option(
            "--listplugins",
            action="callback", callback=cb_list_plugins,
            help="list available Plugooni as plgoos plugin names"
        )

        # --captiveportal
        def cb_captiveportal(option, opt, value, oparser):
            self.action = opt[2:]
        optparser.add_option(
            "--captiveportal",
            action="callback", callback=cb_captiveportal,
            help="run vendor emulated captiveportal tests"
        )

        # --transhttp
        def cb_transhttp(option, opt, value, oparser):
            self.action = opt[2:]
        optparser.add_option(
            "--transhttp",
            action="callback", callback=cb_transhttp,
            help="run Transparent HTTP tests"
        )

        # --dns
        def cb_dnstests(option, opt, value, oparser):
            self.action = opt[2:]
        optparser.add_option(
            "--dns",
            action="callback", callback=cb_dnstests,
            help="run fixed generic dns tests"
        )

        # --dnsbulk
        def cb_dnsbulktests(option, opt, value, oparser):
            self.action = opt[2:]
        optparser.add_option(
            "--dnsbulk",
            action="callback", callback=cb_dnsbulktests,
            help="run bulk DNS tests in random.shuffle() order"
        )

        # --dns-cc-check
        def cb_dnscccheck(option, opt, value, oparser):
            self.action = opt[2:]
        optparser.add_option(
            "--dnscccheck",
            action="callback", callback=cb_dnscccheck,
            help="run cc specific bulk DNS tests in random.shuffle() order"
        )

        # --cc [country code]
        def cb_cc(option, opt, value, optparser):
          # XXX: We should check this against a list of supported county codes
          # and then return the matching value from the list into self.cc
          self.cc = str(value)
        optparser.add_option(
            "--cc", type="string",
            action="callback", callback=cb_cc,
            help="set a specific county code -- default is None",
        )

        # --list [url/hostname/ip list in file]
        def cb_list(option, opt, value, optparser):
          self.listfile = os.path.expanduser(value)
          if not os.path.isfile(self.listfile):
              print "Wrong file '" + value + "' in --list."
              sys.exit(1)
        optparser.add_option(
            "--list", type="string",
            action="callback", callback=cb_list,
            help="file to read from -- default is None",
        )

        # --url [url/hostname/ip]
        def cb_host(option, opt, value, optparser):
          self.hostname = str(value)
        optparser.add_option(
            "--url", type="string",
            action="callback", callback=cb_host,
            help="set URL/hostname/IP for use in tests -- default is None",
        )

        # --controlproxy [scheme://host:port]
        def cb_controlproxy(option, opt, value, optparser):
          self.controlproxy = str(value)
        optparser.add_option(
            "--controlproxy", type="string",
            action="callback", callback=cb_controlproxy,
            help="proxy to be used as a control -- default is None",
        )

        # --experimentproxy [scheme://host:port]
        def cb_experimentproxy(option, opt, value, optparser):
          self.experimentproxy = str(value)
        optparser.add_option(
            "--experimentproxy", type="string",
            action="callback", callback=cb_experimentproxy,
            help="proxy to be used for experiments -- default is None",
        )



        # --randomize
        def cb_randomize(option, opt, value, optparser):
          self.randomize = bool(int(value))
        optparser.add_option(
            "--randomize", type="choice",
            choices=['0', '1'], metavar="0|1",
            action="callback", callback=cb_randomize,
            help="randomize host order -- default is on",
        )

        # XXX TODO:
        # pause/resume scans for dns_BULK_DNS_Tests()
        # setting of control/experiment resolver
        # setting of control/experiment proxy
        #

        def cb_version(option, opt, value, oparser):
            self.action = 'version'
        optparser.add_option(
            "-v", "--version",
            action="callback", callback=cb_version,
            help="print ooni-probe version"
        )

        # parse options
        (opts, args) = optparser.parse_args()

        # validate options
        try:
            if (args):
                raise optparse.OptionError('extra arguments found', args)
            if (not self.action):
                raise optparse.OptionError(
                    'RTFS', 'required arguments missing'
                )

        except optparse.OptionError, err:
            sys.stderr.write(str(err) + '\n\n')
            optparser.print_help()
            sys.exit(1)

    def version(self):
        print """
ooni-probe REcon 2011 pre-alpha
Copyright (c) 2011, Jacob Appelbaum
See: https://www.torproject.org/ooni/

"""

    def run(self):
        getattr(self, self.action)()

    def plugin(self):
        plugin_run = ooni.plugooni.Plugooni
        plugin_run(self).run(self)

    def listplugins(self):
        plugin_run = ooni.plugooni.Plugooni
        plugin_run(self).list_plugoons()

    def captiveportal(self):
        captive_portal = ooni.captive_portal.CaptivePortal
        captive_portal(self).main()

    def transhttp(self):
        transparent_http = ooni.transparenthttp.TransparentHTTPProxy
        transparent_http(self).main()

    def dns(self):
        dnstests = ooni.namecheck.DNS
        dnstests(self).main()

    def dnsbulk(self):
        dnstests = ooni.dns_poisoning.DNSBulk
        dnstests(self).main()

    def dnscccheck(self):
        dnstests = ooni.dns_cc_check.DNSBulk
        dnstests(self).main()


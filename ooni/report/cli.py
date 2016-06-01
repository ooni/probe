from __future__ import print_function

import os
import sys

from ooni import canonical_bouncer
from ooni.report import __version__
from ooni.report import tool
from ooni.settings import config

from twisted.python import usage


class Options(usage.Options):

    synopsis = """%s [options] upload | status
""" % (os.path.basename(sys.argv[0]),)

    optFlags = [
        ["default-collector", "d", "Upload the reports to the default "
                                   "collector that is looked up with the "
                                   "canonical bouncer."]
    ]

    optParameters = [
        ["configfile", "f", None,
         "Specify the configuration file to use."],
        ["collector", "c", None,
         "Specify the collector to upload the result to."],
        ["bouncer", "b", None,
         "Specify the bouncer to query for a collector."]
    ]

    def opt_version(self):
        print("oonireport version: %s" % __version__)
        sys.exit(0)

    def parseArgs(self, *args):
        if len(args) == 0:
            raise usage.UsageError(
                "Must specify at least one command"
            )
            return
        self['command'] = args[0]
        if self['command'] not in ("upload", "status"):
            raise usage.UsageError(
                "Must specify either command upload or status"
            )
        if self['command'] == "upload":
            try:
                self['report_file'] = args[1]
            except IndexError:
                self['report_file'] = None


def tor_check():
    if not config.tor.socks_port:
        print("Currently oonireport requires that you start Tor yourself "
              "and set the socks_port inside of ooniprobe.conf")
        sys.exit(1)


def run():
    options = Options()
    try:
        options.parseOptions()
    except Exception as exc:
        print("Error: %s" % exc)
        print(options)
        sys.exit(2)
    config.global_options = dict(options)
    config.set_paths()
    config.read_config_file()

    if options['default-collector']:
        options['bouncer'] = canonical_bouncer

    if options['command'] == "upload" and options['report_file']:
        tor_check()
        return tool.upload(options['report_file'],
                           options['collector'],
                           options['bouncer'])
    elif options['command'] == "upload":
        tor_check()
        return tool.upload_all(options['collector'],
                               options['bouncer'])
    elif options['command'] == "status":
        return tool.status()
    else:
        print(options)

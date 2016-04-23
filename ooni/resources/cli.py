import sys

from twisted.internet import defer
from twisted.python import usage

from ooni.resources import __version__
from ooni.resources import update


class Options(usage.Options):
    synopsis = """%s
    This is used to update the resources required to run oonideckgen and
    ooniprobe.
    You just run this script with no arguments and it will update the
    resources.
    """ % sys.argv[0]

    optFlags = [
        ["update-inputs", None, "(deprecated) update the resources needed for "
                                "inputs."],
        ["update-geoip", None, "(deprecated) Update the geoip related "
                               "resources."]
    ]
    optParameters = []

    def opt_version(self):
        print("ooniresources version: %s" % __version__)
        sys.exit(0)


@defer.inlineCallbacks
def run():
    options = Options()
    try:
        options.parseOptions()
    except usage.UsageError as error_message:
        print "%s: %s" % (sys.argv[0], error_message)
        print "%s: Try --help for usage details." % (sys.argv[0])
        sys.exit(1)

    if options['update-inputs'] or options['update-geoip']:
        print("WARNING: Passing command line arguments is deprecated")

    yield update.download_resources()

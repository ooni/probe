import sys

from twisted.python import usage

from ooni.resources import __version__
from ooni.resources import update


class Options(usage.Options):
    synopsis = """%s"""

    optParameters = []

    def opt_version(self):
        print("ooniresources version: %s" % __version__)
        sys.exit(0)


def run():
    options = Options()
    try:
        options.parseOptions()
    except usage.UsageError as error_message:
        print "%s: %s" % (sys.argv[0], error_message)
        print "%s: Try --help for usage details." % (sys.argv[0])
        sys.exit(1)

    return update.download_inputs()

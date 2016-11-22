import sys

from twisted.python import usage
from ooni import __version__

class Options(usage.Options):
    synopsis = """%s
    [DEPRECATED] Usage of this script is deprecated and it will be deleted
    in future versions of ooniprobe.
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


def run():
    options = Options()
    try:
        options.parseOptions()
    except usage.UsageError as error_message:
        print "%s: %s" % (sys.argv[0], error_message)
        print "%s: Try --help for usage details." % (sys.argv[0])
        sys.exit(1)

    print("WARNING: Usage of this script is deprecated. We will not do "
          "anything.")
    sys.exit(0)

import sys

from twisted.internet import defer
from twisted.python import usage

from ooni.utils import log

from ooni.resources import __version__
from ooni.resources import update


class Options(usage.Options):
    synopsis = """%s""" % sys.argv[0]

    optFlags = [
        ["update-inputs", None, "Update the resources needed for inputs."],
        ["update-geoip", None, "Update the geoip related resources."]
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

    if not any(options.values()):
        print("%s: no command specified" % sys.argv[0])
        print options
        sys.exit(1)

    if options['update-inputs']:
        print "Downloading inputs"
        try:
            yield update.download_inputs()
        except Exception as exc:
            log.err("failed to download geoip files")
            log.exception(exc)

    if options['update-geoip']:
        print "Downloading geoip files"
        try:
            yield update.download_geoip()
        except Exception as exc:
            log.err("failed to download geoip files")
            log.exception(exc)

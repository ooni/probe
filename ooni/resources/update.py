import os

from twisted.internet import defer
from twisted.web.client import downloadPage

from ooni.settings import config
from ooni.resources import inputs, geoip


@defer.inlineCallbacks
def download_resource(resources):
    for filename, resource in resources.items():
        print "Downloading %s" % filename

        filename = os.path.join(config.resources_directory, filename)
        yield downloadPage(resource['url'], filename)

        if resource['action'] is not None:
            yield defer.maybeDeferred(resource['action'],
                                      filename,
                                      *resource['action_args'])
        print "%s written." % filename


def download_inputs():
    return download_resource(inputs)


def download_geoip():
    return download_resource(geoip)

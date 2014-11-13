import os

from twisted.internet import defer
from twisted.web.client import downloadPage

from ooni.settings import config
from ooni.resources import inputs, geoip
from ooni.utils import unzip, gunzip


@defer.inlineCallbacks
def download_resource(resources):
    for filename, resource in resources.items():
        print "Downloading %s" % filename

        if resource["action"] in [unzip, gunzip] and resource["action_args"]:
                    dirname = resource["action_args"][0]
                    filename = os.path.join(dirname, filename)
        else:
            filename = os.path.join(config.resources_directory, filename)
        if not os.path.exists(filename):
            directory = os.path.dirname(filename)
            if not os.path.isdir(directory):
                os.makedirs(directory)
            f = open(filename, 'w')
            f.close()
        elif not os.path.isfile(filename):
            print "[!] %s must be a file." % filename
            defer.returnValue(False)
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

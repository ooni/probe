"""
This is a self genrated test created by scaffolding.py.
you will need to fill it up with all your necessities.
Safe hacking :).
"""
from zope.interface import implements
from twisted.python import usage
from twisted.plugin import IPlugin
from ooni.plugoo.tests import ITest, OONITest
from ooni.plugoo.assets import Asset
from ooni.protocols import http
from ooni.utils import log

class httptArgs(usage.Options):
    optParameters = [['urls', 'f', None, 'Urls file'],
                     ['url', 'u', 'http://torproject.org/', 'Test single site'],
                     ['resume', 'r', 0, 'Resume at this index']]

class httptTest(http.HTTPTest):
    implements(IPlugin, ITest)

    shortName = "httpt"
    description = "httpt"
    requirements = None
    options = httptArgs
    blocking = False

    def control(self, experiment_result, args):
        # What you return here ends up inside of the report.
        log.msg("Running control")
        return {}

    def load_assets(self):
        if self.local_options and self.local_options['urls']:
            return {'url': Asset(self.local_options['urls'])}
        else:
            return {}

# We need to instantiate it otherwise getPlugins does not detect it
# XXX Find a way to load plugins without instantiating them.
httpt = httptTest(None, None, None)

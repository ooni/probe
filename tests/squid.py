"""
    Squid Proxy Detector
    ********************

"""
import os
import httplib
import urllib2
from urlparse import urlparse

from plugoo import gen_headers
from plugoo.assets import Asset
from plugoo.tests import Test

__plugoo__ = "SquidProxy"
__desc__ = "This Test aims at detecting the squid transparent proxy"

class SquidAsset(Asset):
    """
    This is the asset that should be used by the Test. It will
    contain all the code responsible for parsing the asset file
    and should be passed on instantiation to the test.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)


class Squid(Test):
    """
    Squid Proxy testing class.
    """
    def _http_request(self, method, url,
                      path=None, headers=None):
        """
        Perform an HTTP Request.
        XXX move this function to the core OONI
        code.
        """
        url = urlparse(url)
        host = url.netloc

        conn = httplib.HTTPConnection(host, 80)
        conn.connect()

        if path is None:
            path = purl.path

        conn.putrequest(method, path)

        for h in gen_headers():
            conn.putheaders(h[0], h[1])
        conn.endheaders()

        send_browser_headers(self, None, conn)

        response = conn.getresponse()

        headers = dict(response.getheaders())

        self.headers = headers
        self.data = response.read()
        return True

    def invalid_request(self):
        """
        This will trigger squids "Invalid Request" error.
        """
        pass

    def cache_object(self):
        """
        This attempts to do a GET cache_object://localhost/info on
        any destination and checks to see if the response contains
        is that of Squid.
        """

        pass

    def experiment(self, *a, **kw):
        """
        Fill this up with the tasks that should be performed
        on the "dirty" network and should be compared with the
        control.
        """


    def control(self):
        """
        Fill this up with the control related code.
        """
        return True

def run(ooni):
    """
    This is the function that will be called by OONI
    and it is responsible for instantiating and passing
    the arguments to the Test class.
    """
    config = ooni.config

    # This the assets array to be passed to the run function of
    # the test
    assets = [TestTemplateAsset(os.path.join(config.main.assetdir, \
                                            "someasset.txt"))]

    # Instantiate the Test
    thetest = TestTemplate(ooni)
    ooni.logger.info("starting SquidProxyTest...")
    # Run the test with argument assets
    thetest.run(assets)
    ooni.logger.info("finished.")



"""
    HTTP Host based filtering
    *************************

    This test detect HTTP Host field
    based filtering.
    It is used to detect censorship on
    performed with Web Guard (used by
    T-Mobile US).
"""
import os
from datetime import datetime
from gevent import monkey

import urllib2
import httplib
# WARNING! Using gevent's socket
# introduces the 0x20 DNS "feature".
# This will result is weird DNS requests
# appearing on the wire.
monkey.patch_socket()

try:
    from BeautifulSoup import BeautifulSoup
except:
    print "BeautifulSoup-3.2.1 is missing. Please see https://crate.io/packages/BeautifulSoup/"

from plugoo.assets import Asset
from plugoo.tests import Test

__plugoo__ = "HTTP Host"
__desc__ = "This detects HTTP Host field based filtering"

class HTTPHostAsset(Asset):
    """
    This is the asset that should be used by the Test. It will
    contain all the code responsible for parsing the asset file
    and should be passed on instantiation to the test.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)

    def parse_line(self, line):
        return line.split(',')[1].replace('\n','')

class HTTPHost(Test):
    """
    The main Test class
    """

    def check_response(self, response):
        soup = BeautifulSoup(response)
        if soup.head.title.string == "Content Filtered":
            # Response indicates censorship
            return True
        else:
            # Response does not indicate censorship
            return False


    def is_censored(self, response):
        if response:
            soup = BeautifulSoup(response)
            censored = self.check_response(response)
        else:
            censored = "unreachable"
        return censored

    def urllib2_test(self, control_server, host):
        req = urllib2.Request(control_server)
        req.add_header('Host', host)
        try:
            r = urllib2.urlopen(req)
            response = r.read()
            censored = self.is_censored(response)
        except Exception, e:
            censored = "Error! %s" % e

        return censored

    def httplib_test(self, control_server, host):
        try:
            conn = httplib.HTTPConnection(control_server)
            conn.putrequest("GET", "", skip_host=True, skip_accept_encoding=True)
            conn.putheader("Host", host)
            conn.putheader("User-Agent", "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.6")
            conn.endheaders()
            r = conn.getresponse()
            response = r.read()
            censored = self.is_censored(response)
        except Exception, e:
            censored = "Error! %s" % e

        return censored


    def experiment(self, *a, **kw):
        """
        Try to connect to the control server with
        the specified host field.
        """
        host = kw['data']
        control_server = kw['control_server']
        self.logger.info("Testing %s (%s)" % (host, control_server))

        #censored = self.urllib2_test(control_server, host)
        censored = self.httplib_test(control_server, host)

        self.logger.info("%s: %s" % (host, censored))
        return {'Time': datetime.now(),
                'Host': host,
                'Censored': censored}


def run(ooni):
    """
    This is the function that will be called by OONI
    and it is responsible for instantiating and passing
    the arguments to the Test class.
    """
    config = ooni.config

    # This the assets array to be passed to the run function of
    # the test
    assets = [HTTPHostAsset(os.path.join(config.main.assetdir, \
                                            "top-1m.csv"))]

    # Instantiate the Test
    thetest = HTTPHost(ooni)
    ooni.logger.info("starting HTTP Host Test...")
    # Run the test with argument assets
    thetest.run(assets, {'index': 5825, 'control_server': '195.85.254.203:8080'})
    ooni.logger.info("finished.")



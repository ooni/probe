"""
    TCP Port Scanner
    ****************

    Does a TCP connect scan on the IP:port pairs.

"""
import os
import socket
from datetime import datetime
import socks

from plugoo.assets import Asset
from plugoo.tests import Test

__plugoo__ = "TCP Port Scanner"
__desc__ = "This a test template to be used to build your own tests"

class TCPScanAsset(Asset):
    """
    This is the asset that should be used by the Test. It will
    contain all the code responsible for parsing the asset file
    and should be passed on instantiation to the test.
    """
    def __init__(self, file=None):
        self = Asset.__init__(self, file)


class TCPScan(Test):
    """
    The main Test class
    """

    def experiment(self, *a, **kw):
        """
        Fill this up with the tasks that should be performed
        on the "dirty" network and should be compared with the
        control.
        """
        addr = kw['data']
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        res = False
        try:
            self.logger.debug('Doing a connection to %s' % addr)
            s.connect((addr.split(':')[0], int(addr.split(':')[1])))
            res = True
        except socket.error, msg:
            self.logger.debug('Connection failed to %s: %s' % (addr, msg))

        finally:
            s.close()

        return {'Time': datetime.now(),
                'Address': addr,
                'Status': res}

    def control(self):
        """
        Fill this up with the control related code.
        """
        return True

def run(ooni, asset=None):
    """
    This is the function that will be called by OONI
    and it is responsible for instantiating and passing
    the arguments to the Test class.
    """
    config = ooni.config

    # This the assets array to be passed to the run function of
    # the test
    if asset:
        assets = [TCPScanAsset(asset)]
    else:
        assets = [TCPScanAsset(os.path.join(config.main.assetdir, \
                                            "tcpscan.txt"))]

    # Instantiate the Test
    thetest = TCPScan(ooni)
    ooni.logger.info("starting TCP Scan...")
    # Run the test with argument assets
    thetest.run(assets)
    ooni.logger.info("finished.")



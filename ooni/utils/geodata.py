import re
import os

from twisted.web.client import Agent
from twisted.internet import reactor, defer, protocol

from ooni.utils import log, net
from ooni import config
from ooni.errors import GeoIPDataFilesNotFound

try:
    import pygeoip
except ImportError:
    log.err("Unable to import pygeoip. We will not be able to run geo IP related measurements")

def IPToLocation(ipaddr):
    log.debug("looking up %s" % ipaddr)
    city_file = os.path.join(config.advanced.geoip_data_dir, 'GeoLiteCity.dat')
    country_file = os.path.join(config.advanced.geoip_data_dir, 'GeoIP.dat')
    asn_file = os.path.join(config.advanced.geoip_data_dir, 'GeoIPASNum.dat')

    location = {'city': None, 'countrycode': None, 'asn': None}
    try:
        city_dat = pygeoip.GeoIP(city_file)
        location['city'] = city_dat.record_by_addr(ipaddr)['city']

        country_dat = pygeoip.GeoIP(country_file)
        location['countrycode'] = country_dat.country_code_by_addr(ipaddr)

        asn_dat = pygeoip.GeoIP(asn_file)
        asn = asn_dat.org_by_addr(ipaddr)
        location['asn'] = re.search('AS\d+', asn).group(0)

    except IOError:
        log.err("Could not find GeoIP data files. Go into data/ "
                "and run make geoip")
        raise GeoIPDataFilesNotFound

    return location


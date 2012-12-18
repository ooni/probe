# -*- encoding: utf-8 -*-
#
# geodata.py
# **********
# In here go functions related to the understanding of
# geographical information of the probe
#
# :licence: see LICENSE

import re
import os

from twisted.web.client import Agent
from twisted.internet import reactor, defer, protocol

from ooni.utils import log, net
from ooni import config

try:
    import pygeoip
except ImportError:
    log.err("Unable to import pygeoip. We will not be able to run geo IP related measurements")

class GeoIPDataFilesNotFound(Exception):
    pass

def IPToLocation(ipaddr):
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
        location['asn'] = asn_dat.org_by_addr(ipaddr)
    except IOError:
        try:
            raise GeoIPDataFilesNotFound(
                "Couldn't find GeoIP files. Go to ./data and run \"make geoip\".")
        except GeoIPDataFilesNotFound, gnf:
            log.err(gnf)

    return location


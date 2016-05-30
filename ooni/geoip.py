from __future__ import absolute_import
import re
import os
import random

from hashlib import sha256

from twisted.web import client, http_headers

client._HTTP11ClientFactory.noisy = False

from twisted.internet import reactor, defer

from ooni.utils import log
from ooni import errors

try:
    from pygeoip import GeoIP
except ImportError:
    try:
        import GeoIP as CGeoIP
        def GeoIP(database_path, *args, **kwargs):
            return CGeoIP.open(database_path, CGeoIP.GEOIP_STANDARD)
    except ImportError:
        log.err("Unable to import pygeoip. We will not be able to run geo IP related measurements")

class GeoIPDataFilesNotFound(Exception):
    pass

def IPToLocation(ipaddr):
    from ooni.settings import config

    country_file = config.get_data_file_path('GeoIP/GeoIP.dat')
    asn_file = config.get_data_file_path('GeoIP/GeoIPASNum.dat')

    location = {'city': None, 'countrycode': 'ZZ', 'asn': 'AS0'}
    if not asn_file or not country_file:
        log.err("Could not find GeoIP data file in data directories."
                "Try running ooniresources or"
                " edit your ooniprobe.conf")
        return location

    country_dat = GeoIP(country_file)
    asn_dat = GeoIP(asn_file)

    country_code = country_dat.country_code_by_addr(ipaddr)
    if country_code is not None:
        location['countrycode'] =  country_code

    asn = asn_dat.org_by_addr(ipaddr)
    if asn is not None:
        location['asn'] = asn.split(' ')[0]

    return location

def database_version():
    from ooni.settings import config

    version = {
        'GeoIP': {
            'sha256': None,
            'timestamp': None,
        },
        'GeoIPASNum': {
            'sha256': None,
            'timestamp': None
        }
    }

    for key in version.keys():
        geoip_file = config.get_data_file_path("GeoIP/" + key + ".dat")
        if not geoip_file or not os.path.isfile(geoip_file):
            continue
        timestamp = os.stat(geoip_file).st_mtime

        sha256hash = sha256()
        with open(geoip_file) as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256hash.update(chunk)

        version[key]['timestamp'] = timestamp
        version[key]['sha256'] = sha256hash.hexdigest()
    return version


class HTTPGeoIPLookupper(object):
    url = None

    _agent = client.Agent

    def __init__(self):
        self.agent = self._agent(reactor)

    def _response(self, response):
        from ooni.utils.net import BodyReceiver

        content_length = response.headers.getRawHeaders('content-length')

        finished = defer.Deferred()
        response.deliverBody(BodyReceiver(finished, content_length))
        finished.addCallback(self.parseResponse)
        return finished

    def parseResponse(self, response_body):
        """
        Override this with the logic for parsing the response.

        Should return the IP address of the probe.
        """
        pass

    def failed(self, failure):
        log.err("Failed to lookup via %s" % self.url)
        log.exception(failure)
        return failure

    def lookup(self):
        from ooni.utils.net import userAgents

        headers = {}
        headers['User-Agent'] = [random.choice(userAgents)]

        d = self.agent.request("GET", self.url, http_headers.Headers(headers))
        d.addCallback(self._response)
        d.addErrback(self.failed)
        return d

class UbuntuGeoIP(HTTPGeoIPLookupper):
    url = "http://geoip.ubuntu.com/lookup"

    def parseResponse(self, response_body):
        m = re.match(".*<Ip>(.*)</Ip>.*", response_body)
        probe_ip = m.group(1)
        return probe_ip

class TorProjectGeoIP(HTTPGeoIPLookupper):
    url = "https://check.torproject.org/"

    def parseResponse(self, response_body):
        regexp = "Your IP address appears to be:  <strong>((\d+\.)+(\d+))"
        probe_ip = re.search(regexp, response_body).group(1)
        return probe_ip

class ProbeIP(object):
    strategy = None
    address = None

    def __init__(self):
        self.geoIPServices = {
            'ubuntu': UbuntuGeoIP,
            'torproject': TorProjectGeoIP
        }
        self.geodata = {
            'asn': 'AS0',
            'city': None,
            'countrycode': 'ZZ',
            'ip': '127.0.0.1'
        }

    def resolveGeodata(self):
        from ooni.settings import config

        self.geodata = IPToLocation(self.address)
        self.geodata['ip'] = self.address
        if not config.privacy.includeasn:
            self.geodata['asn'] = 'AS0'
        if not config.privacy.includecountry:
            self.geodata['countrycode'] = 'ZZ'
        if not config.privacy.includeip:
            self.geodata['ip'] = '127.0.0.1'

    @defer.inlineCallbacks
    def lookup(self):
        if self.address:
            defer.returnValue(self.address)
        else:
            try:
                yield self.askTor()
                log.msg("Found your IP via Tor")
                self.resolveGeodata()
                defer.returnValue(self.address)
            except errors.TorStateNotFound:
                log.debug("Tor is not running. Skipping IP lookup via Tor.")
            except Exception:
                log.msg("Unable to lookup the probe IP via Tor.")

            try:
                yield self.askGeoIPService()
                log.msg("Found your IP via a GeoIP service")
                self.resolveGeodata()
                defer.returnValue(self.address)
            except Exception:
                log.msg("Unable to lookup the probe IP via GeoIPService")
                raise

    @defer.inlineCallbacks
    def askGeoIPService(self):
        # Shuffle the order in which we test the geoip services.
        services = self.geoIPServices.items()
        random.shuffle(services)
        for service_name, service in services:
            s = service()
            log.msg("Looking up your IP address via %s" % service_name)
            try:
                self.address = yield s.lookup()
                self.strategy = 'geo_ip_service-' + service_name
                break
            except Exception:
                log.msg("Failed to lookup your IP via %s" % service_name)

        if not self.address:
            raise errors.ProbeIPUnknown

    def askTor(self):
        """
        Obtain the probes IP address by asking the Tor Control port via GET INFO
        address.

        XXX this lookup method is currently broken when there are cached descriptors or consensus documents
        see: https://trac.torproject.org/projects/tor/ticket/8214
        """
        from ooni.settings import config

        if config.tor_state:
            d = config.tor_state.protocol.get_info("address")
            @d.addCallback
            def cb(result):
                self.strategy = 'tor_get_info_address'
                self.address = result.values()[0]
            return d
        else:
            raise errors.TorStateNotFound

import re
import os
import random

from twisted.web import client, http_headers
from ooni.utils.net import userAgents, BodyReceiver
from twisted.internet import reactor, defer, protocol

from ooni.utils import log, net, checkForRoot
from ooni.settings import config
from ooni import errors

try:
    from pygeoip import GeoIP
except ImportError:
    try:
        import GeoIP as CGeoIP
        def GeoIP(database_path, *args, **kwargs):
            return CGeoIP.open(database_path)
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
        city_dat = GeoIP(city_file)
        location['city'] = city_dat.record_by_addr(ipaddr)['city']

        country_dat = GeoIP(country_file)
        location['countrycode'] = country_dat.country_code_by_addr(ipaddr)

        asn_dat = GeoIP(asn_file)
        location['asn'] = asn_dat.org_by_addr(ipaddr).split(' ')[0]

    except IOError:
        log.err("Could not find GeoIP data files. Go into data/ "
                "and run make geoip")
        raise GeoIPDataFilesNotFound

    return location

class HTTPGeoIPLookupper(object):
    url = None

    _agent = client.Agent

    def __init__(self):
        self.agent = self._agent(reactor)

    def _response(self, response):
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
        regexp = "Your IP address appears to be: <b>((\d+\.)+(\d+))"
        probe_ip = re.search(regexp, response_body).group(1)
        return probe_ip

class MaxMindGeoIP(HTTPGeoIPLookupper):
    url = "https://www.maxmind.com/en/locate_my_ip"

    def parseResponse(self, response_body):
        regexp = '<span id="my-ip-address">((\d+\.)+(\d+))</span>'
        probe_ip = re.search(regexp, response_body).group(1)
        return probe_ip

class ProbeIP(object):
    strategy = None
    address = None

    def __init__(self):
        self.tor_state = config.tor_state
        self.geoIPServices = {'ubuntu': UbuntuGeoIP,
            'torproject': TorProjectGeoIP,
            'maxmind': MaxMindGeoIP
        }

    @defer.inlineCallbacks
    def lookup(self):
        try:
            yield self.askTor()
            log.msg("Found your IP via Tor %s" % self.address)
            defer.returnValue(self.address)
        except errors.TorStateNotFound:
            log.debug("Tor is not running. Skipping IP lookup via Tor.")
        except Exception:
            log.msg("Unable to lookup the probe IP via Tor.")

        try:
            yield self.askTraceroute()
            log.msg("Found your IP via Traceroute %s" % self.address)
            defer.returnValue(self.address)
        except errors.InsufficientPrivileges:
            log.debug("Cannot determine the probe IP address with a traceroute, becase of insufficient priviledges")
        except:
            log.msg("Unable to lookup the probe IP via traceroute")

        try:
            yield self.askGeoIPService()
            log.msg("Found your IP via a GeoIP service: %s" % self.address)
            defer.returnValue(self.address)
        except Exception, e:
            log.msg("Unable to lookup the probe IP via GeoIPService")
            raise e

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
            except Exception, e:
                log.msg("Failed to lookup your IP via %s" % service_name)

        if not self.address:
            raise errors.ProbeIPUnknown

    def askTraceroute(self):
        """
        Perform a UDP traceroute to determine the probes IP address.
        """
        checkForRoot()
        raise NotImplemented

    def askTor(self):
        """
        Obtain the probes IP address by asking the Tor Control port via GET INFO
        address.

        XXX this lookup method is currently broken when there are cached descriptors or consensus documents
        see: https://trac.torproject.org/projects/tor/ticket/8214
        """
        if self.tor_state:
            d = self.tor_state.protocol.get_info("address")
            @d.addCallback
            def cb(result):
                self.strategy = 'tor_get_info_address'
                self.address = result.values()[0]
            return d
        else:
            raise errors.TorStateNotFound

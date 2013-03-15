from twisted.web import server, static, resource
from twisted.internet import reactor
from twisted.trial import unittest
from twisted.python.filepath import FilePath
from twisted.protocols.policies import WrappingFactory

from ooni.geoip import ProbeIP, MaxMindGeoIP, TorProjectGeoIP
from ooni.geoip import UbuntuGeoIP, HTTPGeoIPLookupper, IPToLocation

class UbuntuGeoIPResource(resource.Resource):
    def render(self, request):
        return """
        <Response>
        <Ip>127.0.0.1</Ip>
        <Spam>Ham</Spam>
        </Response>
        """

class MaxMindGeoIPResource(resource.Resource):
    def render(self, request):
        return """
        <span id="my-ip-address">127.0.0.1</span>
        """

class TorProjectGeoIPResource(resource.Resource):
    def render(self, request):

        return """
        Your IP address appears to be: <b>127.0.0.1</b>
        """

class GeoIPBaseTest(unittest.TestCase):
    services = {'ubuntu': UbuntuGeoIPResource,
            'maxmind': MaxMindGeoIPResource,
            'torproject': TorProjectGeoIPResource
    }
    def _listen(self, site):
        return reactor.listenTCP(0, site, interface="127.0.0.1")

    def setUp(self):
        r = resource.Resource()
        for name, service in self.services.items():
            r.putChild(name, service())
        self.site = server.Site(r, timeout=None)

        self.wrapper = WrappingFactory(self.site)
        self.port = self._listen(self.wrapper)
        self.portno = self.port.getHost().port

    def getUrl(self, service_name):
        return "http://%s:%s/%s" % ('127.0.0.1', self.portno, service_name)

    def tearDown(self):
        return self.port.stopListening()

class TestGeoIPServices(GeoIPBaseTest):
    def test_torproject_geoip(self):
        gip = TorProjectGeoIP()
        gip.url = self.getUrl('torproject')
        d = gip.lookup()
        @d.addCallback
        def cb(res):
            self.assertEqual(res, '127.0.0.1')
        return d

    def test_ubuntu_geoip(self):
        gip = UbuntuGeoIP()
        gip.url = self.getUrl('ubuntu')
        d = gip.lookup()
        @d.addCallback
        def cb(res):
            self.assertEqual(res, '127.0.0.1')
        return d

    def test_maxmind_geoip(self):
        gip = MaxMindGeoIP()
        gip.url = self.getUrl('maxmind')
        d = gip.lookup()
        @d.addCallback
        def cb(res):
            self.assertEqual(res, '127.0.0.1')
        return d

class TestProbeIP(GeoIPBaseTest):
    def setUp(self):
        GeoIPBaseTest.setUp(self)

        # Override the service addresses with those of the fake localhost
        # resource.
        self.probe_ip = ProbeIP()
        for name in self.probe_ip.geoIPServices.keys():
            self.probe_ip.geoIPServices[name].url = self.getUrl(name)

    def test_ask_geoip_service(self):
        d = self.probe_ip.askGeoIPService()
        @d.addCallback
        def cb(res):
            self.assertEqual(self.probe_ip.address, '127.0.0.1')
        return d

    def test_ask_traceroute_service(self):
        pass

    def test_ask_tor(self):
        pass

class TestIPToLocation(unittest.TestCase):
    pass


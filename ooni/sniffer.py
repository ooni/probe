import re
import sys

from ooni.utils.txscapy import ScapyProtocol
from ooni.settings import config
from ooni.utils import log

from scapy.all import TCP, UDP, DNS
from scapy.config import conf


class LibraryNotInstalledError(Exception):
    pass


def pcapdnet_installed():
    """
    Checks to see if libdnet or libpcap are installed and set the according
    variables.

    Returns:

        True
            if pypcap and libdnet are installed

        False
            if one of the two is absent
    """
    # In debian libdnet is called dumbnet instead of dnet, but scapy is
    # expecting "dnet" so we try and import it under such name.
    try:
        import dumbnet

        sys.modules['dnet'] = dumbnet
    except ImportError:
        pass

    try:
        conf.use_pcap = True
        conf.use_dnet = True
        from scapy.arch import pcapdnet

        config.pcap_dnet = True

    except ImportError as e:
        log.err(e.message + ". Pypcap or dnet are not properly installed. Certain tests may not work.")
        config.pcap_dnet = False
        conf.use_pcap = False
        conf.use_dnet = False

    # This is required for unix systems that are different than linux (OSX for
    # example) since scapy explicitly wants pcap and libdnet installed for it
    # to work.
    try:
        from scapy.arch import pcapdnet
    except ImportError:
        log.err("Your platform requires having libdnet and libpcap installed.")
        raise LibraryNotInstalledError

    return config.pcap_dnet


if pcapdnet_installed():
    from scapy.all import PcapWriter

else:
    class DummyPcapWriter:
        def __init__(self, pcap_filename, *arg, **kw):
            log.err("Initializing DummyPcapWriter. We will not actually write to a pcapfile")

        @staticmethod
        def write(self):
            pass

    PcapWriter = DummyPcapWriter


class Filter(object):
    def __init__(self):
        self.rules = {}
        self._ip_regex = re.compile('([0-9]{1,3}\.){3}[0-9]{1,3}$')

    def add_ip_rule(self, dst=None, src=None):
        self.rules['dst'] = dst
        self.rules['src'] = src

    def add_tcp_rule(self, dport=None, sport=None):
        if not 'udp' in self.rules or not self.rules['udp']:
            self.rules['tcp'] = True
            self.rules['dport'] = dport
            self.rules['sport'] = sport

    def add_udp_rule(self, dport=None, sport=None):
        if not 'tcp' in self.rules or not self.rules['tcp']:
            self.rules['udp'] = True
            self.rules['dport'] = dport
            self.rules['sport'] = sport

    def add_http_rule(self, url):
        if not 'dns_host' in self.rules:
            self.rules['http_url'] = url

    def add_dns_rule(self, host):
        if not 'http_url' in self.rules:
            self.rules['dns_host'] = host

    def matches(self, packet):
        matches = []
        if 'dst' in self.rules and self.rules['dst'] is not None:
            dst = packet.fields['dst']
            matches.append(dst == self.rules['dst'])
        if 'src' in self.rules and self.rules['src'] is not None:
            src = packet.fields['src']
            matches.append(src == self.rules['src'])

        if 'tcp' in self.rules and self.rules['tcp']:
            matches.append(isinstance(packet.payload, TCP))
        elif 'udp' in self.rules and self.rules['udp']:
            matches.append(isinstance(packet.payload, UDP))

        if 'dport' in self.rules and self.rules['dport'] is not None:
            dport = packet.payload.fields['dport']
            matches.append(dport == self.rules['dport'])
        if 'sport' in self.rules and self.rules['sport'] is not None:
            sport = packet.payload.fields['sport']
            matches.append(sport == self.rules['sport'])

        if 'http_url' in self.rules:
            payload = packet.payload.payload.original
            splitted = self.rules['http_url'].split('/')
            if 'http' in splitted[0]:
                host = splitted[2]
                resource = '/'.join(splitted[3:])
            else:
                host = splitted[0]
                resource = '/'.join(splitted[1:])

            # This is too unrestricted
            if len(resource) == 0:
                if re.match(self._ip_regex, host):
                    dst = packet.fields['dst']
                    matches.append(dst == host)
                else:
                    has_http_method = re.match('(GET|POST|PUT|HEAD|PUT|DELETE)', payload)
                    matches.append(has_http_method is not None)
            elif len(resource) > 0:
                matches.append(resource in payload)
        elif 'dns_host' in self.rules:
            payload = packet.payload.payload.original
            url = self.rules['dns_host'].split('.')
            matches.append(all([chunk in payload for chunk in url]))

        return all(matches)


class ScapySniffer(ScapyProtocol):
    def __init__(self, pcap_filename, *arg, **kw):
        self.pcapwriter = PcapWriter(pcap_filename, *arg, **kw)
        self.debug = PcapWriter('debug.pcap', *arg, **kw)
        self._conns = []
        self._filters = []

    def add_filter(self, filter):
        if isinstance(filter, Filter):
            self._filters.append(filter)

    def del_filter(self, filter):
        if filter in self._filters:
            self._filters.remove(filter)

    def packetReceived(self, packet):
        try:
            src = packet.fields['src']
            dst = packet.fields['dst']
            sport = packet.payload.fields['sport']
            dport = packet.payload.fields['dport']
        except KeyError:
            return

        selected = False
        for conn in self._conns:
            is_sent = (src == conn['src'] and dst == conn['dst'] and sport == conn['sport'] and dport == conn['dport'])
            is_recv = (src == conn['dst'] and dst == conn['src'] and sport == conn['dport'] and dport == conn['sport'])
            if is_sent or is_recv:
                selected = True

        if not selected:
            for filter in self._filters:
                if filter.matches(packet):
                    selected = True
                    conn = {'src': src, 'dst': dst, 'sport': sport, 'dport': dport}
                    self._conns.append(conn)
                    break

        if selected:
            self.pcapwriter.write(packet)

    def close(self):
        self.pcapwriter.close()

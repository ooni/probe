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


class ScapySniffer(ScapyProtocol):
    def __init__(self, pcap_filename, *arg, **kw):
        self.pcapwriter = PcapWriter(pcap_filename, *arg, **kw)
        if config.advanced.debug:
            self.debug = PcapWriter('debug.pcap', *arg, **kw)
        self._conns = []
        # A filter is {'dns_query': '', 'http_url': '', 'tdport': 0, 'udport': 0, 'dst': ''}
        self.filters = []
        self.ip_regex = re.compile('([0-9]{1,3}\.){3}[0-9]{1,3}$')

    def packetReceived(self, packet):
        selected = False
        try:
            src = packet.fields['src']
            dst = packet.fields['dst']
            sport = packet.payload.fields['sport']
            dport = packet.payload.fields['dport']
        except KeyError:
            return

        for conn in self._conns:
            if (src == conn['src'] and dst == conn['dst'] and sport == conn['sport'] and dport == conn['dport']) or \
                    (src == conn['dst'] and dst == conn['src'] and sport == conn['dport'] and dport == conn['sport']):
                selected = True
                break

        if not selected:
            for filter in self.filters:
                for key, value in filter.items():
                    if value:
                        if key == 'dst' and dst == value:
                            selected = True
                        elif key == 'tdport' and isinstance(packet.payload, TCP) and dport == value:
                            selected = True
                        elif key == 'udport' and isinstance(packet.payload, UDP) and dport == value:
                            selected = True
                        elif key == 'dns_query' and isinstance(packet.payload.payload, DNS):
                            payload = packet.payload.payload.original
                            url = value.split('.')
                            selected = all([chunk in payload for chunk in url])
                        elif key == 'http_url' and isinstance(packet.payload, TCP):
                            payload = packet.payload.payload.original
                            splitted = value.split('/')
                            if 'http' in splitted[0]:
                                host = splitted[2]
                                resource = '/'.join(splitted[3:])
                            else:
                                host = splitted[0]
                                resource = '/'.join(splitted[1:])

                            if len(resource) == 0:
                                if re.match(self.ip_regex, host):
                                    selected = dst == host
                                else:
                                    matched = re.match('(GET|POST|PUT|HEAD|PUT|DELETE) /', payload)
                                    selected = matched is not None
                            elif len(resource) > 0:
                                selected = resource in payload
                if selected:
                    conn = {'src': src, 'dst': dst, 'sport': sport, 'dport': dport}
                    self._conns.append(conn)
                    break

        if selected:
            self.pcapwriter.write(packet)

        if config.advanced.debug:
            self.debug.write(packet)

    def close(self):
        self.pcapwriter.close()

import sys

from scapy.config import conf

from ooni.utils.net import getClientPlatform
from ooni.utils import log
from ooni.settings import config
from ooni.utils import generate_filename
from ooni.utils.txscapy import ScapyProtocol
from ooni.errors import LibraryNotInstalledError


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
    def __init__(self, testDetails, *arg, **kw):
        self.test_name = testDetails['test_name']
        self.private_ip = None
        self.iface = None
        self.platform = None
        self.supported_platforms = ['LINUX', 'OPENBSD', 'FREEBSD', 'NETBSD', 'DARWIN']

        if not config.reports.pcap:
            prefix = 'report'
        else:
            prefix = config.reports.pcap
        filename = config.global_options['reportfile'] if 'reportfile' in config.global_options.keys() else None
        filename_pcap = generate_filename(testDetails, filename=filename, prefix=prefix, extension='pcap')
        self.pcapwriter = PcapWriter(filename_pcap, *arg, **kw)

        self.setup_interface()

    def setup_interface(self):
        self.platform = getClientPlatform()
        if not self.platform in self.supported_platforms:
            log.err('Platform not supported for pcap recording')
            return

        self.private_ip = ip_generator.next_ip()

        if 'LINUX' == self.platform or 'BSD' in self.platform:
            self.attach_ip_linux()
        elif 'DARWIN' == self.platform:
            self.attach_ip_osx()

    def attach_ip_linux(self):
        pass

    def attach_ip_osx(self):
        pass

    def packetReceived(self, packet):
        if self.private_ip is not None:
            if 'src' in packet.fields and (packet.src == self.private_ip or packet.dst == self.private_ip):
                self.pcapwriter.write(packet)

    def close(self):
        # TODO: Clean interfaces, which can be None!!
        self.pcapwriter.close()


class IPGenerator(object):
    def __init__(self, start_ip=40):
        pass

    def next_ip(self):
        return None
ip_generator = IPGenerator()
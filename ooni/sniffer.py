import sys
from distutils.spawn import find_executable

from scapy.config import conf

from twisted.internet import defer, reactor

from ooni.utils.net import getClientPlatform
from ooni.utils import log
from ooni.settings import config
from ooni.utils import generate_filename
from ooni.utils.txscapy import ScapyProtocol
from ooni.utils.net import getDefaultIface, getNetworksFromRoutes, isHostAlive, AsyncProcess
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
    """
        If it's impossible to setup the sniffer, self.private_ip and self.iface must be None
    """
    def __init__(self, testDetails, *arg, **kw):
        self.IFNAMSIZ = 16 - 1
        self.test_name = testDetails['test_name']
        self.private_ip = None
        self.masked_ip = None
        self.iface = None
        self.index = None
        self.platform = None
        self.supported_platforms = ['LINUX', 'OPENBSD', 'FREEBSD', 'NETBSD', 'DARWIN']

        if not config.reports.pcap:
            prefix = 'report'
        else:
            prefix = config.reports.pcap
        filename = config.global_options['reportfile'] if 'reportfile' in config.global_options.keys() else None
        filename_pcap = generate_filename(testDetails, filename=filename, prefix=prefix, extension='pcap')
        self.pcapwriter = PcapWriter(filename_pcap, *arg, **kw)

    def clear(self):
        self.private_ip = self.iface = None

    @defer.inlineCallbacks
    def setup_interface(self):
        self.platform = getClientPlatform()
        if not self.platform in self.supported_platforms:
            log.err('Platform not supported for pcap recording')
            return

        self.masked_ip = yield ip_generator.next_ip()
        if self.masked_ip is not None:
            self.private_ip = self.masked_ip.split('/')[0]
            if 'LINUX' == self.platform or 'BSD' in self.platform:
                self.attach_ip_linux()
            elif 'DARWIN' == self.platform:
                self.attach_ip_osx()

    def attach_ip_linux(self):
        from pyroute2 import IPDB, IPRoute

        self.gen_iface()
        try:
            ipdb = IPDB()
            with ipdb.create(kind='dummy', ifname=self.iface) as i:
                i.add_ip(self.masked_ip)

            route = IPRoute()
            for r in route.get_addr():
                for attr in r['attrs']:
                    if attr[0] == 'IFA_LABEL' and attr[1] == self.iface:
                        self.index = r['index']
            route.link_up(self.index)
        except Exception:
            self.clear()

    def gen_iface(self):
        self.iface = self.test_name
        if len(self.iface) > self.IFNAMSIZ:
            self.iface = ''
            rev = self.test_name.split('_')[::-1]
            length = len(rev)*2 - 1
            for chunk in rev:
                if length - 1 + len(chunk) <= self.IFNAMSIZ:
                    self.iface = '%s_%s' % (chunk, self.iface)
                    length += len(chunk) - 1
                else:
                    self.iface = '%s_%s' % (chunk[0], self.iface)
            self.iface = self.iface[:-1]

    def detach_ip_linux(self):
        from pyroute2 import IPRoute

        route = IPRoute()
        if self.index is not None:
            route.link_remove(self.index)

    def attach_ip_osx(self):
        def err_cb(reason):
            self.private_ip = self.iface = None
        ifconfig = find_executable('ifconfig')
        if len(ifconfig) > 0:
            self.iface = ip_generator.default_iface
            d = defer.Deferred()
            process = AsyncProcess(d)
            d.addErrback(err_cb)
            reactor.spawnProcess(process, ifconfig, ['ifconfig', self.iface, 'alias', self.masked_ip])
            process.transport.signalProcess('TERM')
        else:
            self.clear()

    def detach_ip_osx(self):
        def err_cb(reason):
            log.err('%s cannot be removed from %s' % (self.private_ip, self.iface))
        ifconfig = find_executable('ifconfig')
        if len(ifconfig) > 0:
            d = defer.Deferred()
            process = AsyncProcess(d)
            d.addErrback(err_cb)
            reactor.spawnProcess(process, ifconfig, ['ifconfig', self.iface, '-alias', self.masked_ip])
            process.transport.signalProcess('TERM')

    def packetReceived(self, packet):
        if self.private_ip is not None:
            if 'src' in packet.fields and (packet.src == self.private_ip or packet.dst == self.private_ip):
                self.pcapwriter.write(packet)

    def close(self):
        self.pcapwriter.close()

        if self.private_ip is not None:
            if 'LINUX' == self.platform or 'BSD' in self.platform:
                self.detach_ip_linux()
            elif 'DARWIN' == self.platform:
                self.detach_ip_osx()


class IPGenerator(object):
    def __init__(self, start_ip='40'):
        self.subnet = None
        self.current_ip = None
        self.default_iface = getDefaultIface()

        networks = getNetworksFromRoutes()
        subnets = [n for n in networks if n.iface == self.default_iface and n.compressed != '0.0.0.0/0']
        if len(subnets) > 1:
            log.msg('More than one default subnet was detected, you should double check that the sniffer is working')
        elif len(subnets) == 0:
            log.msg('None subnet was found for %s' % self.default_iface)
            log.debug('networks:')
            for network in networks:
                log.debug('%s(%s)' % (network.iface, network.compressed))
        else:
            self.subnet = subnets[0]

            if self.subnet.prefixlen != 24:
                log.err('The netmask of the subnet %s must be 24')
                self.current_ip = None
            else:
                template = self.subnet.ip.compressed.split('.')
                template[-1] = str(start_ip)
                self.current_ip = '.'.join(template)

    @defer.inlineCallbacks
    def next_ip(self):
        if self.current_ip is not None:
            template = self.current_ip.split('.')
            n = int(template[-1]) + 1
            template[-1] = str(n)
            isAlive = yield isHostAlive(self.current_ip)
            while isAlive:
                self.current_ip = '.'.join(template)
                n += 1
                template[-1] = str(n)
                isAlive = yield isHostAlive(self.current_ip)
            old_ip = self.current_ip
            self.current_ip = '.'.join(template)
            defer.returnValue(old_ip + '/' + str(self.subnet.prefixlen))
        defer.returnValue(None)
ip_generator = IPGenerator()
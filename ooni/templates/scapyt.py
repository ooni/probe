from scapy.all import TCP, UDP

from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni.settings import config
from ooni.utils.net import hasRawSocketPermission

from ooni.utils.txscapy import ScapySender, ScapyFactory
from ooni.sniffer import Filter


class BaseScapyTest(NetTestCase):

    """
    The report of a test run with scapy looks like this:

    report:
        sent_packets: [
            {
            'raw_packet': BASE64Encoding of packet,
            'summary': 'IP / TCP 192.168.2.66:ftp_data > 8.8.8.8:http S'
            }
        ]

        answered_packets: []

    """
    name = "Base Scapy Test"
    version = 0.1

    requiresRoot = not hasRawSocketPermission()
    baseFlags = [
        ['ipsrc', 's',
         'Does *not* check if IP src and ICMP IP citation '
         'matches when processing answers'],
        ['seqack', 'k',
         'Check if TCP sequence number and ACK match in the '
         'ICMP citation when processing answers'],
        ['ipid', 'i', 'Check if the IPID matches when processing answers']]

    def _setUp(self):
        super(BaseScapyTest, self)._setUp()

        if config.scapyFactory is None:
            log.debug("Scapy factory not set, registering it.")
            config.scapyFactory = ScapyFactory(config.advanced.interface)

        self.report['answer_flags'] = []
        if self.localOptions['ipsrc']:
            config.checkIPsrc = 0
        else:
            self.report['answer_flags'].append('ipsrc')
            config.checkIPsrc = 1

        if self.localOptions['ipid']:
            self.report['answer_flags'].append('ipid')
            config.checkIPID = 1
        else:
            config.checkIPID = 0
        # XXX we don't support strict matching
        # since (from scapy's documentation), some stacks have a bug for which
        # the bytes in the IPID are swapped.
        # Perhaps in the future we will want to have more fine grained control
        # over this.

        if self.localOptions['seqack']:
            self.report['answer_flags'].append('seqack')
            config.check_TCPerror_seqack = 1
        else:
            config.check_TCPerror_seqack = 0

        self.report['sent_packets'] = []
        self.report['answered_packets'] = []

    def finishedSendReceive(self, packets):
        """
        This gets called when all packets have been sent and received.
        """
        if self.sniffer is not None:
            for sniffer_filter in self.__sniffer_filters:
                self.sniffer.del_filter(sniffer_filter)
        answered, unanswered = packets

        for snd, rcv in answered:
            log.debug("Writing report for scapy test")
            sent_packet = snd
            received_packet = rcv

            if not config.privacy.includeip:
                log.debug("Detected you would not like to "
                          "include your ip in the report")
                log.debug(
                    "Stripping source and destination IPs from the reports")
                sent_packet.src = '127.0.0.1'
                received_packet.dst = '127.0.0.1'

            self.report['sent_packets'].append(sent_packet)
            self.report['answered_packets'].append(received_packet)
        return packets

    def add_filters(self, packets):
        if not isinstance(packets, list):
            packets = list(packets)
        self.__sniffer_filters = []
        for packet in packets:
            sniffer_filter = Filter()
            self.sniffer.add_filter(sniffer_filter)
            self.__sniffer_filters.append(sniffer_filter)

            src = dst = None
            if 'src' in packet.fields:
                src = packet.fields['src']
            if 'dst' in packet.fields:
                dst = packet.fields['dst']
            sniffer_filter.add_ip_rule(dst=dst, src=src)

            if 'payload' in dir(packet):
                sport = dport = None
                if 'sport' in packet.payload.fields:
                    sport = packet.payload.fields['sport']
                if 'dport' in packet.payload.fields:
                    dport = packet.payload.fields['dport']
                if isinstance(packet.payload, TCP):
                    sniffer_filter.add_tcp_rule(dport=dport, sport=sport)
                elif isinstance(packet.payload, UDP):
                    sniffer_filter.add_udp_rule(dport=dport, sport=sport)

    def sr(self, packets, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.sr for sending and receiving of packets
        at layer 3.
        """
        if self.sniffer is not None:
            self.add_filters(packets)
        scapySender = ScapySender()

        config.scapyFactory.registerProtocol(scapySender)
        log.debug("Using sending with hash %s" % scapySender.__hash__)

        d = scapySender.startSending(packets)
        d.addCallback(self.finishedSendReceive)
        return d

    def sr1(self, packets, *arg, **kw):
        def done(packets):
            """
            We do this so that the returned value is only the one packet that
            we expected a response for, identical to the scapy implementation
            of sr1.
            """
            try:
                return packets[0][0][1]
            except IndexError:
                log.err("Got no response...")
                return packets

        if self.sniffer is not None:
            self.add_filters(packets)
        scapySender = ScapySender()
        scapySender.expected_answers = 1

        config.scapyFactory.registerProtocol(scapySender)

        log.debug("Running sr1")
        d = scapySender.startSending(packets)
        log.debug("Started to send")
        d.addCallback(self.finishedSendReceive)
        d.addCallback(done)
        return d

    def send(self, packets, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.send for sending of packets at layer 3
        """
        if self.sniffer is not None:
            self.add_filters(packets)
        scapySender = ScapySender()

        config.scapyFactory.registerProtocol(scapySender)
        scapySender.startSending(packets)

        scapySender.stopSending()
        for sent_packet in packets:
            self.report['sent_packets'].append(sent_packet)


ScapyTest = BaseScapyTest

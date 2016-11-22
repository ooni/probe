from base64 import b64encode
from ooni.nettest import NetTestCase
from ooni.utils import log
from ooni.settings import config
from ooni.utils.net import hasRawSocketPermission

from ooni.utils.txscapy import ScapySender, ScapyFactory


def representPacket(packet):
    return {
        "raw_packet": {
            'data': b64encode(str(packet)),
            'format': 'base64'
        },
        "summary": str(repr(packet))
    }

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

            self.report['sent_packets'].append(representPacket(sent_packet))
            self.report['answered_packets'].append(representPacket(received_packet))
        return packets

    def sr(self, packets, timeout=None, *arg, **kw):
        """
        Wrapper around scapy.sendrecv.sr for sending and receiving of packets
        at layer 3.
        """
        scapySender = ScapySender(timeout=timeout)

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
        scapySender = ScapySender()

        config.scapyFactory.registerProtocol(scapySender)
        scapySender.startSending(packets)

        scapySender.stopSending()
        for sent_packet in packets:
            self.report['sent_packets'].append(representPacket(sent_packet))


ScapyTest = BaseScapyTest

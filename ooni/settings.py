import os
import sys
import yaml
import getpass

from twisted.internet import defer, reactor
from twisted.internet.endpoints import TCP4ClientEndpoint

from os.path import abspath, expanduser
from scapy.all import get_if_list
import txtorcon

from ooni import otime, geoip
from ooni.utils import Storage, log
from ooni import errors


class OConfig(object):
    _custom_home = None

    def __init__(self):
        self.current_user = getpass.getuser()
        self.global_options = {}
        self.reports = Storage()
        self.scapyFactory = None
        self.tor_state = None
        # This is used to store the probes IP address obtained via Tor
        self.probe_ip = geoip.ProbeIP()
        # This is used to keep track of the state of the sniffer
        self.sniffer_running = None
        self.logging = True
        self.basic = Storage()
        self.advanced = Storage()
        self.tor = Storage()
        self.privacy = Storage()
        self.set_paths()

    def set_paths(self, ooni_home=None):
        if ooni_home:
            self._custom_home = ooni_home

        if self.global_options.get('datadir'):
            self.data_directory = abspath(expanduser(self.global_options['datadir']))
        elif self.advanced.get('data_dir'):
            self.data_directory = self.advanced['data_dir']
        elif hasattr(sys, 'real_prefix'):
            self.data_directory = os.path.abspath(os.path.join(sys.prefix, 'share', 'ooni'))
        else:
            self.data_directory = '/usr/share/ooni/'

        self.nettest_directory = abspath(os.path.join(__file__, '..', 'nettests'))

        self.ooni_home = os.path.join(expanduser('~'+self.current_user), '.ooni')
        if self._custom_home:
            self.ooni_home = self._custom_home
        self.inputs_directory = os.path.join(self.ooni_home, 'inputs')
        self.decks_directory = os.path.join(self.ooni_home, 'decks')
        self.reports_directory = os.path.join(self.ooni_home, 'reports')
        self.report_log_file = os.path.join(self.ooni_home, 'reporting.yml')

        if self.global_options.get('configfile'):
            config_file = self.global_options['configfile']
            self.config_file = expanduser(config_file)
        else:
            self.config_file = os.path.join(self.ooni_home, 'ooniprobe.conf')

        if 'logfile' in self.basic:
            self.basic.logfile = expanduser(self.basic.logfile.replace('~','~'+self.current_user))

    def initialize_ooni_home(self, ooni_home=None):
        if ooni_home:
            self.set_paths(ooni_home)

        if not os.path.isdir(self.ooni_home):
            print "Ooni home directory does not exist."
            print "Creating it in '%s'." % self.ooni_home
            os.mkdir(self.ooni_home)
            os.mkdir(self.inputs_directory)
            os.mkdir(self.decks_directory)
        if not os.path.isdir(self.reports_directory):
            os.mkdir(self.reports_directory)

    def _create_config_file(self):
        sample_config_file = os.path.join(self.data_directory,
                                          'ooniprobe.conf.sample')
        target_config_file = self.config_file
        print "Creating it for you in '%s'." % target_config_file
        usr_share_path = '/usr/share'
        if hasattr(sys, 'real_prefix'):
            usr_share_path = os.path.abspath(os.path.join(sys.prefix, 'share'))

        with open(sample_config_file) as f:
            with open(target_config_file, 'w+') as w:
                for line in f:
                    if line.startswith('    data_dir: '):
                        w.write('    data_dir: %s\n' % os.path.join(usr_share_path, 'ooni'))
                    elif line.startswith('    geoip_data_dir: '):
                        w.write('    geoip_data_dir: %s\n' % os.path.join(usr_share_path, 'GeoIP'))
                    else:
                        w.write(line)

    @defer.inlineCallbacks
    def read_config_file(self, check_incoherences=False):
        if not os.path.exists(self.config_file):
            print "Configuration file does not exist."
            self._create_config_file()
            self.read_config_file()

        with open(self.config_file) as f:
            config_file_contents = '\n'.join(f.readlines())
            configuration = yaml.safe_load(config_file_contents)

        for setting in configuration.keys():
            if setting in dir(self):
                for k, v in configuration[setting].items():
                    getattr(self, setting)[k] = v
        self.set_paths()

        # The incoherent checks must be performed after OConfig is in a valid state to runWithDirector
        if check_incoherences:
            coherent = yield self.check_incoherences(configuration)
            if not coherent:
                raise errors.ConfigFileIncoherent

    @defer.inlineCallbacks
    def check_incoherences(self, configuration):
        incoherent = []
        deferreds = []

        if not configuration['advanced']['start_tor']:
            if not 'socks_port' in configuration['tor']:
                incoherent.append('tor:socks_port')
            if not 'control_port' in configuration['tor']:
                incoherent.append('tor:control_port')
            if 'socks_port' in configuration['tor'] and 'control_port' in configuration['tor']:
                # Check if tor is listening in these ports
                @defer.inlineCallbacks
                def cb(state):
                    timeout_call.cancel()
                    result = yield state.protocol.get_info("net/listeners/socks")
                    if result["net/listeners/socks"].split(':')[1] != str(configuration['tor']['socks_port']):
                        incoherent.append('tor:socks_port')

                def err(failure):
                    incoherent.append('tor:socks_port')
                    if timeout_call.active:
                        timeout_call.cancel()

                def timeout():
                    incoherent.append('tor:control_port')
                    if not d.called:
                        d.errback()

                connection = TCP4ClientEndpoint(reactor, "localhost", configuration['tor']['control_port'])
                d = txtorcon.build_tor_connection(connection)
                d.addCallback(cb)
                d.addErrback(err)
                deferreds.append(d)
                timeout_call = reactor.callLater(30, timeout)

        if configuration['advanced']['interface'] != 'auto' and configuration['advanced']['interface'] not in get_if_list():
            incoherent.append('advanced:interface')

        deferred_list = defer.DeferredList(deferreds)
        yield deferred_list
        if len(incoherent) > 0:
            if len(incoherent) > 1:
                incoherent_pretty = ", ".join(incoherent[:-1]) + ' and ' + incoherent[-1]
            else:
                incoherent_pretty = incoherent[0]
            log.err("You must set properly %s in %s." % (incoherent_pretty, self.config_file))
            defer.returnValue(False)
        defer.returnValue(True)

    def generate_pcap_filename(self, testDetails):
        test_name, start_time = testDetails['test_name'], testDetails['start_time']
        start_time = otime.epochToTimestamp(start_time)
        return "report-%s-%s.%s" % (test_name, start_time, "pcap")

config = OConfig()
